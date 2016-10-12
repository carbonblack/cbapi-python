#!/usr/bin/env python

from __future__ import absolute_import

import contextlib
import copy
import json
from distutils.version import LooseVersion
from collections import namedtuple, defaultdict
import base64
from datetime import datetime, timedelta
from zipfile import ZipFile
from contextlib import closing
import struct
from six.moves import urllib
import six
import logging

from cbapi.utils import convert_query_params
from ..errors import InvalidObjectError, ApiError
from ..oldmodels import BaseModel, MutableModel, immutable

if six.PY3:
    long = int
    from io import BytesIO as StringIO
else:
    from cStringIO import StringIO

from ..models import NewBaseModel, MutableBaseModel, CreatableModelMixin
from ..oldmodels import BaseModel, immutable
from .utils import convert_from_cb, convert_from_solr, parse_42_guid, convert_event_time
from ..errors import ServerError, InvalidHashError, ObjectNotFoundError
from ..query import SimpleQuery

try:
    from functools import total_ordering
except ImportError:
    from total_ordering import total_ordering

from six import python_2_unicode_compatible, iteritems

# Get constants for decoding the Netconn events
import socket


log = logging.getLogger(__name__)


# class Process(NewBaseModel):
#     swagger_meta_file = "response/models/process.yaml"
#     urlobject = '/api/v1/process'
#
#     def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False):
#         if type(initial_data) == dict:
#             # workaround for CbER where parent_unique_id is returned as null
#             # string as part of a query result. in this case we need to do a
#             # full_init. TODO: add this to quirks when this is fixed by Cb.
#             for attrname in ['parent_unique_id', 'parent_name', 'parent_md5']:
#                 initial_data.pop(attrname)
#
#         super(Process, self).__init__(cb, model_unique_id, initial_data, force_init)


# class Binary(NewBaseModel):
#     primary_key = "md5"
#     swagger_meta_file = "response/models/binary.yaml"
#     urlobject = '/api/v1/binary'


class BannedHash(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/v1/banning/blacklist"
    swagger_meta_file = "response/models/hash_blacklist.yaml"
    primary_key = "md5hash"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    @property
    def binary(self):
        return self._join(Binary, "md5hash")

    def _update_object(self):
        if "enabled" in self._dirty_attributes:
            # Emulate the strange behavior we have to do for banned hashes.
            # - if we are enabling a hash, just "POST" to the root urlobject.
            # - if we are disabling a hash, just "DELETE" the specific object.
            #   note that disabling a hash also removes the "text" from the object. save it back.

            if self.enabled:
                ret = self._cb.api_json_request(self.__class__._new_object_http_method, self.__class__.urlobject,
                                                data=self._info)
                self._dirty_attributes = {}
                return self._refresh_if_needed(ret)
            else:
                ret = self._cb.delete_object(self._build_api_request_uri())
                del(self._dirty_attributes["enabled"])
                if self.text:
                    self._dirty_attributes["text"] = None

                if self.is_dirty():
                    return super(BannedHash, self)._update_object()
                else:
                    return self._refresh_if_needed(ret)
        else:
            return super(BannedHash, self)._update_object()


class Site(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/site"
    swagger_meta_file = "response/models/site.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    def _parse(self, info):
        if info is None or len(info) != 1:
            raise ObjectNotFoundError(uri=self._build_api_request_uri())
        return info[0]

    @property
    def throttle_rules(self):
        return self._cb.select(ThrottleRule).where("site_id:{0}".format(self.id))

    def __init__(self, cb, site_id=None, initial_data=None, **kwargs):
        super(Site, self).__init__(cb, site_id, initial_data, **kwargs)

        if initial_data:
            self._full_init = True


# TODO: we cannot modify/create Throttle rules until the semantics around the POST/PUT handler are fixed
class ThrottleRule(NewBaseModel):
    urlobject = "/api/throttle"
    swagger_meta_file = "response/models/throttle.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    @property
    def site(self):
        return self._join(Site, "site_id")


class Alert(MutableBaseModel):
    urlobject = "/api/v1/alert"
    swagger_meta_file = "response/models/alert.yaml"
    _change_object_http_method = "POST"
    primary_key = "unique_id"

    def __init__(self, cb, alert_id, initial_data=None):
        super(Alert, self).__init__(cb, alert_id, initial_data)

    def _refresh(self):
        # there is no GET method for an Alert.
        return True

    @property
    def process(self):
        if 'process' in self.alert_type:
            return self._cb.select(Process, self.process_id, getattr(self, "segment_id", 1))
        return None

    @property
    def binary(self):
        return self._join(Binary, "md5")

    @property
    def sensor(self):
        return self._join(Sensor, "sensor_id")

    @property
    def feed(self):
        return self._join(Feed, "feed_id")

    @property
    def trigger_ioc(self):
        return self.ioc_attr


class Feed(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/feed.yaml"
    urlobject = '/api/v1/feed'

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    def _search(self, cls, min_score=None, max_score=None):
        if not self.enabled:
            return

        feed_name = self.name
        if not feed_name:
            raise InvalidObjectError("Feed has no name")

        if not max_score:
            max_score = "*"
        if not min_score:
            min_score = "1"

        min_score = str(min_score)
        max_score = str(max_score)

        return self._cb.select(cls).where("alliance_score_{0:s}:[{1:s} TO {2:s}]".format(feed_name.lower(),
                                                                                         min_score, max_score))

    def search_processes(self, min_score=None, max_score=None):
        return self._search(Process, min_score, max_score)

    def search_binaries(self, min_score=None, max_score=None):
        return self._search(Binary, min_score, max_score)

    @property
    def actions(self):
        return self._cb.select(FeedAction).where("group_id:{0}".format(int(self._model_unique_id)))

    @property
    def reports(self):
        return self._cb.select(ThreatReport).where("feed_id:{0}".format(int(self._model_unique_id)))

    def create_action(self):
        new_action = self._cb.create(FeedAction)
        new_action.group_id = int(self._model_unique_id)
        return new_action


class ActionTypes(object):
    TYPE_MAP = {
        0: "email",
        1: "syslog",
        2: "http_post",
        3: "alert"
    }

    R_TYPE_MAP = dict((value, key) for key, value in iteritems(TYPE_MAP))

    @classmethod
    def string_for_type(cls, typ):
        return cls.TYPE_MAP.get(typ, "unknown")

    @classmethod
    def type_for_string(cls, s):
        if s not in cls.R_TYPE_MAP:
            raise ApiError("Unknown Action type: {}".format(s))
        return cls.R_TYPE_MAP[s]


class FeedAction(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/feedaction.yaml"

    @property
    def urlobject(self):
        return self._build_api_request_uri()

    def _build_api_request_uri(self):
        if self._model_unique_id:
            return "/api/v1/feed/{0}/action/{1}".format(self.feed_id, self._model_unique_id)
        else:
            return "/api/v1/feed/{0}/action".format(self.feed_id)

    def _retrieve_cb_info(self):
        # Can't "get" a feedaction
        return self._info

    @classmethod
    def _query_implementation(cls, cb):
        return ArrayQuery(cls, cb, "group_id", urlbuilder=lambda x: "/api/v1/feed/{0}/action".format(int(x)))

    @property
    def feed_id(self):
        return self.group_id

    @property
    def feed(self):
        return self._join(Feed, "group_id")

    @property
    def type(self):
        return ActionTypes.string_for_type(self.action_type)

    @type.setter
    def type(self, s):
        self.action_type = ActionTypes.type_for_string(s)


class WatchlistAction(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/watchlistaction.yaml"

    @property
    def urlobject(self):
        return self._build_api_request_uri()

    def _build_api_request_uri(self):
        if self._model_unique_id:
            return "/api/v1/watchlist/{0}/action/{1}".format(self.watchlist_id, self._model_unique_id)
        else:
            return "/api/v1/watchlist/{0}/action".format(self.watchlist_id)

    def _retrieve_cb_info(self):
        # Can't "get" a watchlistaction
        return self._info

    @classmethod
    def _query_implementation(cls, cb):
        return ArrayQuery(cls, cb, "watchlist_id", urlbuilder=lambda x: "/api/v1/watchlist/{0}/action".format(int(x)))

    @property
    def watchlist_id(self):
        return self.group_id

    @property
    def watchlist(self):
        return self._join(Watchlist, "watchlist_id")

    @property
    def type(self):
        return ActionTypes.string_for_type(self.action_type)

    @type.setter
    def type(self, s):
        self.action_type = ActionTypes.type_for_string(s)


class Sensor(MutableBaseModel):
    swagger_meta_file = "response/models/sensorObject.yaml"
    urlobject = '/api/v1/sensor'
    NetworkAdapter = namedtuple('NetworkAdapter', ['macaddr', 'ipaddr'])

    def __init__(self, *args, **kwargs):
        super(Sensor, self).__init__(*args, **kwargs)

    @classmethod
    def _query_implementation(cls, cb):
        return SensorQuery(cls, cb)

    @property
    def group(self):
        return self._join(SensorGroup, "group_id")

    @group.setter
    def group(self, new_group):
        self.group_id = new_group

    @property
    def dns_name(self):
        return getattr(self, 'computer_dns_name', None)

    @property
    def hostname(self):
        return getattr(self, 'computer_name', None)

    @property
    def network_interfaces(self):
        out = []
        for adapter in getattr(self, 'network_adapters', '').split('|'):
            parts = adapter.split(',')
            if len(parts) == 2:
                out.append(Sensor.NetworkAdapter._make([':'.join(a+b for a,b in zip(parts[1][::2], parts[1][1::2])),
                                                        parts[0]]))
        return out

    @property
    def os(self):
        return getattr(self, 'os_environment_display_string', None)

    @property
    def registration_time(self):
        return convert_from_cb(getattr(self, 'registration_time', -1))

    @property
    def sid(self):
        return getattr(self, 'computer_sid')

    @property
    def webui_link(self):
        return '{0:s}/#/host/{1}'.format(self._cb.url, self._model_unique_id)

    # TODO: properly handle the stats api routes
    @property
    def queued_stats(self):
        return self._cb.get_object("{0}/queued".format(self._build_api_request_uri()), default=[])

    @property
    def activity_stats(self):
        return self._cb.get_object("{0}/activity".format(self._build_api_request_uri()), default=[])

    @property
    def resource_status(self):
        return self._cb.get_object("{0}/resourcestatus".format(self._build_api_request_uri()), default=[])

    def lr_session(self):
        """
        Retrieve a Live Response session object for this Sensor.

        :return: Live Response session object
        :rtype: :py:class:`cbapi.live_response_api.LiveResponseSession`
        :raises ApiError: if there is an error establishing a Live Response session for this Sensor
        """
        if not getattr(self, "supports_cblr", False):
            raise ApiError("Sensor does not support Cb Live Response")

        return self._cb._request_lr_session(self._model_unique_id)

    def flush_events(self):
        self.event_log_flush_time = datetime.now() + timedelta(days=1)
        self.save()


class SensorGroup(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/group-modify.yaml"
    urlobject = '/api/group'

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    def _parse(self, obj):
        # for some reason, these are returned as an array of size one
        if obj and len(obj):
            return obj[0]
        else:
            raise ObjectNotFoundError(uri=self._build_api_request_uri())

    @property
    def sensors(self):
        return self._cb.select(Sensor).where("groupid:{0:s}".format(str(self._model_unique_id)))

    def get_installer(self, osname="windows/exe"):
        target_url = "/api/v1/group/{0}/installer/{1:s}".format(self._model_unique_id, osname)
        with closing(self._cb.session.get(target_url, stream=True)) as r:
            return r.content

    @property
    def site(self):
        return self._join(Site, "site_id")

    @site.setter
    def site(self, new_site):
        self.site_id = new_site.id


class SensorQuery(SimpleQuery):
    valid_field_names = ['ip', 'hostname', 'groupid']

    def __init__(self, cls, cb):
        super(SensorQuery, self).__init__(cls, cb)

    def where(self, new_query):
        nq = super(SensorQuery, self).where(new_query)
        for k, v in iteritems(nq._query):
            if k not in SensorQuery.valid_field_names:
                nq._query = {}
                raise ValueError("Field name must be one of: {0:s}".format(", ".join(SensorQuery.valid_field_names)))

        return nq

    @property
    def results(self):
        if not self._full_init:
            full_results = self._cb.get_object(self._urlobject, query_parameters=convert_query_params(self._query))
            if not full_results:
                self._results = []
            else:
                self._results = [self._doc_class.new_object(self._cb, it, full_doc=True) for it in full_results]
            self._results = self._sort(self._results)
            self._full_init = True

        return self._results


class User(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/user.yaml"
    urlobject = "/api/user"
    primary_key = "username"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb, "/api/users")

    def __init__(self, cb, *args, **kwargs):
        super(User, self).__init__(cb, *args, **kwargs)
        self._info["id"] = self._model_unique_id

    def _retrieve_cb_info(self):
        info = super(User, self)._retrieve_cb_info()
        info["id"] = self._model_unique_id
        return info


class Watchlist(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/watchlist-new.yaml"
    urlobject = '/api/v1/watchlist'

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    def __init__(self, *args, **kwargs):
        self._query_template = {"cb.urlver": 1}
        super(Watchlist, self).__init__(*args, **kwargs)

    @property
    def _query(self):
        sq = getattr(self, "search_query", None)
        if sq is not None:
            return urllib.parse.parse_qsl(getattr(self, "search_query", ""))
        else:
            return []

    @property
    def query(self):
        queryparams = [(k, v) for k, v in self._query if k == "q" or k.startswith("cb.q.")]
        queryparts = []
        for k, v in queryparams:
            if k == 'q':
                queryparts.append(v)
            else:
                queryparts.append("{0}:{1}".format(k[5:], v))

        return " ".join(queryparts)

    def _reset_query(self):
        qt = list(self._query)
        new_q = []
        template_items = self._query_template.copy()

        for k, v in qt:
            if k == "q" or k.startswith("cb.q."):
                pass
            else:
                new_q.append((k, v))

            if k in template_items:
                del template_items[k]

        for k, v in iteritems(template_items):
            new_q.append((k, v))

        self.search_query = urllib.parse.urlencode(new_q)

    @query.setter
    def query(self, new_query):
        self._reset_query()
        qt = list(self._query)
        qt.append(("q", new_query))
        self.search_query = "&".join(("{0}={1}".format(k, urllib.parse.quote(v)) for k,v in qt))

    @property
    def facets(self):
        facets = {}
        for k, v in self._query:
            if k.startswith("cb.fq."):
                facets[k[6:]] = v

        return facets

    def search(self):
        search_query = getattr(self, "search_query", "")
        index_type = getattr(self, "index_type", "events")

        if index_type == 'events':
            return self._cb.select(Process, raw_query=search_query)
        elif index_type == 'modules':
            return self._cb.select(Binary, raw_query=search_query)
        else:
            raise InvalidObjectError("index_type of {0:s} is invalid".format(index_type))

    @property
    def actions(self):
        return self._cb.select(WatchlistAction).where("watchlist_id:{0}".format(int(self._model_unique_id)))

    def create_action(self):
        new_action = self._cb.create(WatchlistAction)
        new_action.watchlist_id = int(self._model_unique_id)
        return new_action


class ArrayQuery(SimpleQuery):
    def __init__(self, cls, cb, valid_field_name, urlbuilder):
        super(ArrayQuery, self).__init__(cls, cb)
        self._results_last_query = []
        self._results_last_id = None
        self.valid_field_name = valid_field_name
        self.urlbuilder = urlbuilder

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb, self.valid_field_name, self.urlbuilder)
        nq._results_last_id = self._results_last_id
        nq._results_last_query = self._results_last_query[::]
        nq._query = copy.deepcopy(self._query)

        return nq

    def where(self, new_query):
        nq = super(ArrayQuery, self).where(new_query)
        for k, v in iteritems(nq._query):
            if k != nq.valid_field_name:
                nq._query = {}
                raise ValueError("Field name must be: {0:s}".format(self.valid_field_name))

        return nq

    def _build_object(self, item):
        return self._doc_class.new_object(self._cb, item)

    @property
    def results(self):
        if not self._query.get(self.valid_field_name, None):
            raise ApiError("Must use a search parameter: .where('{0:s}:<id>')".format(self.valid_field_name))
        if self._results_last_id != self._query[self.valid_field_name]:
            self._results_last_id = self._query[self.valid_field_name]
            res = self._cb.get_object(self.urlbuilder(self._query[self.valid_field_name]))
            if res and type(res) == list:
                self._results_last_query = [self._build_object(it) for it in res]
            else:
                self._results_last_query = []

        return self._results_last_query


class TaggedEvent(MutableBaseModel, CreatableModelMixin):
    urlobject = '/api/tagged_event'
    swagger_meta_file = "response/models/tagged_event.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return ArrayQuery(cls, cb, "investigation_id",
                          urlbuilder=lambda x: TaggedEvent.urlobject + "/{0:d}".format(int(x)))

    def _refresh(self):
        # there is no GET method for a TaggedEvent.
        return True

    @property
    def investigation(self):
        return self.select(Investigation).where("id:{0}".format(self.investigation_id))

    @property
    def process(self):
        process_guid = getattr(self, "unique_id", None)
        process_segment = getattr(self, "segment_id", 1)
        if process_guid:
            return self._cb.select(Process, process_guid, process_segment)
        else:
            return None


class Investigation(MutableBaseModel):
    urlobject = '/api/investigations'
    swagger_meta_file = "response/models/investigation.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    def _refresh(self):
        # there is no GET method for an Investigation.
        return True

    @property
    def events(self):
        return self._cb.select(TaggedEvent).where("investigation_id:{0}".format(self._model_unique_id))


class TaggedModel(BaseModel):
    def __init__(self, *args, **kwargs):
        self._tags = defaultdict(dict)
        self._tags_init = False
        super(TaggedModel, self).__init__(*args, **kwargs)

    @property
    def tags(self):
        if not self._tags_init:
            self._init_tags()

        return self._tags.keys()

    def _init_tags(self):
        if not self._full_init:
            self._retrieve_cb_info()

        for field_name in self._info.keys():
            parts = field_name.split("_")
            if len(parts) == 3 and parts[0] == "alliance":
                self._tags[parts[2]][parts[1]] = self._info[field_name]

    # TODO: DRY
    # TODO: should these raise a ValueError if no such tag exists? I am leaning toward "yes"
    def tag_data(self, tag_name):
        if not self._tags_init:
            self._init_tags()

        return self._tags.get(tag_name, {}).get("data", None)

    def tag_score(self, tag_name):
        if not self._tags_init:
            self._init_tags()

        return self._tags.get(tag_name, {}).get("score", None)

    def tag_link(self, tag_name):
        if not self._tags_init:
            self._init_tags()

        return self._tags.get(tag_name, {}).get("link", None)

    def tag_info(self, tag_name):
        if not self._tags_init:
            self._init_tags()

        return self._tags.get(tag_name, {})


class ThreatReport(MutableBaseModel):
    urlobject = '/api/v1/threat_report'
    primary_key = "_internal_id"

    @property
    def _model_unique_id(self):
        feed_id = getattr(self, "feed_id")
        report_id = getattr(self, "id")

        if feed_id and report_id:
            return "{0}:{1}".format(feed_id, report_id)
        else:
            return None

    def disable(self):
        self.is_ignored = True
        self.save()

    def enable(self):
        self.is_ignored = False
        self.save()

    @classmethod
    def new_object(cls, cb, item, **kwargs):
        return cb.select(ThreatReport, "%s:%s" % (item["feed_id"], item["id"]), initial_data=item)

    def _build_api_request_uri(self):
        return "/api/v1/feed/{0:s}/report/{1:s}".format(str(self.feed_id), self.id)

    def __init__(self, cb, full_id, initial_data=None):
        if not initial_data:
            try:
                # fill in feed_id and id
                (feed_id, report_id) = full_id.split(":")
                initial_data = { "feed_id": feed_id, "id": report_id }
            except:
                raise ApiError("ThreatReport ID must be in form '<feed_id>:<report_id>'")

        super(ThreatReport, self).__init__(cb, full_id, initial_data)

    @property
    def feed(self):
        return self._join(Feed, "feed_id")

    def _update_object(self):
        update_content = { "ids": { str(self.feed_id): [str(self.id)] }, "updates": {}}
        for k in self._dirty_attributes.keys():
            update_content["updates"][k] = getattr(self, k)

        ret = self._cb.post_object(ThreatReport.urlobject, update_content)

        if ret.status_code not in (200, 204):
            try:
                message = json.loads(ret.content)[0]
            except:
                message = ret.content

            raise ServerError(ret.status_code, message,
                              result="Did not update {} record.".format(self.__class__.__name__))
        else:
            try:
                message = ret.json()
                if message.keys() == ["result"]:
                    post_result = message.get("result", None)

                    if post_result and post_result != "success":
                        raise ServerError(ret.status_code, post_result,
                                          result="Did not update {0:s} record.".format(self.__class__.__name__))
                    else:
                        self.refresh()
                else:
                    self._info = json.loads(ret.content)
                    self._full_init = True
            except:
                self.refresh()

        self._dirty_attributes = {}
        return self._model_unique_id


@immutable
class Binary(TaggedModel):
    VirusTotal = namedtuple('VirusTotal', ['score', 'link'])
    SigningData = namedtuple('SigningData', ['result', 'publisher', 'issuer', 'subject', 'sign_time', 'program_name'])
    VersionInfo = namedtuple('VersionInfo', ['file_desc', 'file_version', 'product_name', 'product_version',
                                             'company_name', 'legal_copyright', 'original_filename'])
    FrequencyData = namedtuple('FrequencyData', ['computer_count', 'process_count', 'all_process_count',
                                                 'module_frequency'])

    urlobject = '/api/v1/binary'

    @property
    def _stat_titles(self):
        titles = super(Binary, self)._stat_titles
        if "icon" in titles:
            titles.remove("icon")
        return titles

    @classmethod
    def new_object(cls, cb, item):
        return cb.select(Binary, item['md5'], initial_data=item)

    def __init__(self, cb, md5sum, initial_data=None, force_init=False):
        md5sum = md5sum.upper()
        if len(md5sum) != 32:
            raise InvalidHashError("MD5sum {} is not valid".format(md5sum))

        super(Binary, self).__init__(cb, md5sum, initial_data)

        self.md5sum = md5sum
        self._frequency = None

        if force_init:
            self.refresh()

    def _build_api_request_uri(self):
        return Binary.urlobject + "/{0:s}/summary".format(self.md5sum)

    @property
    def webui_link(self):
        return '{0:s}/#binary/{1:s}'.format(self._cb.url, self.md5sum)

    @property
    def frequency(self):
        if not self._frequency:
            r = self._cb.get_object('/api/v1/process/host/count',
                                    query_parameters=(('cb.freqver', 1), ('name', 'md5'), ('md5', self.md5sum)))
            self._frequency = r

            hostCount = self._frequency.get('hostCount', 0)
            globalCount = self._frequency.get('globalCount', 0)
            numDocs = self._frequency.get('numDocs', 0)
            if numDocs == 0:
                frequency_fraction = 0.0
            else:
                frequency_fraction = float(globalCount) / float(numDocs)

            # TODO: frequency calculated over number of hosts rather than number of processes
            self._frequency = Binary.FrequencyData._make([hostCount, globalCount, numDocs, frequency_fraction])

        return self._frequency

    @property
    def file(self):
        # TODO: I don't like reaching through to the session...
        with closing(self._cb.session.get("/api/v1/binary/{0:s}".format(self.md5sum), stream=True)) as r:
            z = StringIO(r.content)
            zf = ZipFile(z)
            fp = zf.open('filedata')
            return fp

    @property
    def observed_filenames(self):
        return self._attribute('observed_filename', [])

    @property
    def size(self):
        return long(self._attribute('orig_mod_len', 0))

    @property
    def copied_size(self):
        return long(self._attribute('copied_mod_len', 0))

    @property
    def endpoints(self):
        endpoint_list = self._attribute('endpoint', [])
        return [self._cb.select(Sensor, int(endpoint.split("|")[1]),
                                initial_data={"computer_name": endpoint.split("|")[0]})
                for endpoint in endpoint_list]

    @property
    def version_info(self):
        return Binary.VersionInfo._make([self._attribute('file_desc', ""), self._attribute('file_version', ""),
                                         self._attribute('product_name', ""), self._attribute('product_version', ""),
                                         self._attribute('company_name', ""), self._attribute('legal_copyright', ""),
                                         self._attribute('original_filename', "")])

    # Returns True if the binary contains a valid digital signature.
    # Returns False if the binary has no digital signature, if the signature is expired or otherwise
    # distrusted.
    @property
    def signed(self):
        if self._attribute('digsig_result') == 'Signed':
            return True
        else:
            return False

    @property
    def signing_data(self):
        digsig_sign_time = self._attribute('digsig_sign_time', "")
        if digsig_sign_time:
            digsig_sign_time = convert_from_cb(digsig_sign_time)

        return Binary.SigningData._make([self._attribute('digsig_result', ""),
                                         self._attribute('digsig_publisher', ""),
                                         self._attribute('digsig_issuer', ""),
                                         self._attribute('digsig_subject', ""),
                                         digsig_sign_time,
                                         self._attribute('digsig_prog_name', "")])

    @property
    def digsig_publisher(self):
        return self._attribute('digsig_publisher', "")

    @property
    def digsig_issuer(self):
        return self._attribute('digsig_issuer', "")

    @property
    def digsig_subject(self):
        return self._attribute('digsig_subject', "")

    @property
    def digsig_sign_time(self):
        return self._attribute('digsig_sign_time', "")

    @property
    def digsig_prog_name(self):
        return self._attribute('digsig_prog_name', "")

    @property
    def is_64bit(self):
        return self._attribute('is_64bit', False)

    @property
    def is_executable_image(self):
        return self._attribute('is_executable_image', False)

    @property
    def virustotal(self):
        virustotal_score = self._attribute('alliance_score_virustotal', 0)
        if virustotal_score:
            ret = Binary.VirusTotal._make([int(virustotal_score), self._attribute('alliance_link_virustotal', "")])
        else:
            ret = Binary.VirusTotal._make([0, ''])
        return ret

    @property
    def icon(self):
        icon = ''
        try:
            icon = self._attribute('icon')
            if not icon:
                icon = ''
        except:
            pass

        return base64.b64decode(icon)

    @property
    def banned(self):
        try:
            bh = self._cb.select(BannedHash, self.md5sum.lower())
            bh.refresh()
        except ServerError as e:
            if e.error_code == 409:
                return False
        except ObjectNotFoundError:
            return False
        else:
            return bh


class ProcessV1Parser(object):
    def __init__(self, process_model):
        self.process_model = process_model

    def parse_modload(self, seq, raw_modload):
        parts = raw_modload.split('|')
        new_mod = {}
        timestamp = convert_event_time(parts[0])
        new_mod['md5'] = parts[1]
        new_mod['path'] = parts[2]

        # use the cached data from the parent if possible
        binaries = self.process_model._attribute('binaries', {})
        md5 = new_mod['md5'].upper()
        return CbModLoadEvent(self.process_model, timestamp, seq, new_mod, binary_data=binaries.get(md5, None))

    def parse_filemod(self, seq, filemod):
        def _lookup_type(filemodtype):
            if filemodtype == 1:
                return 'CreatedFile'
            elif filemodtype == 2:
                return 'FirstWrote'
            elif filemodtype == 4:
                return 'Deleted'
            elif filemodtype == 8:
                return 'LastWrote'

        def _lookup_filetype(filetype):
            if filetype == 1:
                return 'PE'
            elif filetype == 2:
                return 'ELF'
            elif filetype == 3:
                return 'MachO'
            elif filetype == 8:
                return 'EICAR'
            elif filetype == 0x10:
                return 'DOC'
            elif filetype == 0x11:
                return 'DOCX'
            elif filetype == 0x30:
                return 'PDF'
            elif filetype == 0x40:
                return 'ZIP'
            elif filetype == 0x41:
                return 'LZH'
            elif filetype == 0x42:
                return 'LZW'
            elif filetype == 0x43:
                return 'RAR'
            elif filetype == 0x44:
                return 'TAR'
            elif filetype == 0x45:
                return '7Z'
            else:
                return 'Unknown'

        if not filemod:
            return

        parts = filemod.split('|')
        new_file = {}
        new_file['type'] = _lookup_type(int(parts[0]))
        timestamp = convert_event_time(parts[1])
        new_file['path'] = parts[2]
        new_file['md5'] = parts[3]
        new_file['filetype'] = 'Unknown'
        if len(parts) > 4 and parts[4] != '':
            new_file['filetype'] = _lookup_filetype(int(parts[4]))

        new_file['tamper_flag'] = False
        if len(parts) > 5 and parts[5] == 'true':
            new_file['tamper_flag'] = True

        return CbFileModEvent(self.process_model, timestamp, seq, new_file)

    def parse_netconn(self, seq, netconn):
        parts = netconn.split('|')
        new_conn = {}
        timestamp = convert_event_time(parts[0])
        try:
            new_conn['remote_ip'] = socket.inet_ntoa(struct.pack('>i', int(parts[1])))
        except:
            new_conn['remote_ip'] = '0.0.0.0'
        new_conn['remote_port'] = int(parts[2])
        new_conn['proto'] = protocols[int(parts[3])]
        new_conn['domain'] = parts[4]
        if parts[5] == 'true':
            new_conn['direction'] = 'Outbound'
        else:
            new_conn['direction'] = 'Inbound'

        return CbNetConnEvent(self.process_model, timestamp, seq, new_conn)

    def parse_regmod(self, seq, regmod):
        def _lookup_type(regmodtype):
            if regmodtype == 1:
                return 'CreatedKey'
            elif regmodtype == 2:
                return 'FirstWrote'
            elif regmodtype == 4:
                return 'DeletedKey'
            elif regmodtype == 8:
                return 'DeletedValue'

        parts = regmod.split('|')
        new_regmod = {}
        timestamp = convert_event_time(parts[1])
        new_regmod['type'] = _lookup_type(int(parts[0]))
        new_regmod['path'] = parts[2]

        new_regmod['tamper_flag'] = False
        if len(parts) > 3 and parts[3] == 'true':
            new_regmod['tamper_flag'] = True

        return CbRegModEvent(self.process_model, timestamp, seq, new_regmod)

    def parse_childproc(self, seq, childproc):
        parts = childproc.split('|')
        timestamp = convert_event_time(parts[0])
        new_childproc = {}
        new_childproc['procguid'] = parts[1]
        new_childproc['md5'] = parts[2]
        new_childproc['path'] = parts[3]
        new_childproc['pid'] = parts[4]

        # TODO: better handling of process start/terminate
        new_childproc['terminated'] = False
        if parts[5] == 'true':
            new_childproc['terminated'] = True

        new_childproc['tamper_flag'] = False
        if len(parts) > 6 and parts[6] == 'true':
            new_childproc['tamper_flag'] = True

        return CbChildProcEvent(self.process_model, timestamp, seq, new_childproc)

    def parse_crossproc(self, seq, raw_crossproc):
        def _lookup_privilege(privilege_code):
            if privilege_code == 0x1FFFFF:
                return 'PROCESS_ALL_ACCESS'
            elif privilege_code == 0x001F0000:
                return 'STANDARD_RIGHTS_ALL'
            elif privilege_code == 0x000F0000:
                return 'STANDARD_RIGHTS_REQUIRED'
            elif privilege_code == 0x00020000:
                return 'STANDARD_RIGHTS_READ'

            # for the rest, then add "or" for each component.
            components = []
            for element in windows_rights_dict.keys():
                if (privilege_code & element) == element:
                    components.append(windows_rights_dict[element])

            return " | ".join(components)

        parts = raw_crossproc.split('|')
        new_crossproc = {}
        timestamp = convert_event_time(parts[1])

        # Types currently supported: RemoteThread and ProcessOpen
        new_crossproc['type'] = parts[0]

        # subtype is only valid for ProcessOpen
        if new_crossproc['type'] == 'ProcessOpen' and int(parts[5]) == 2:
            # this is a thread open not a process open
            new_crossproc['type'] = 'ThreadOpen'

        try:
            privilege = int(parts[6])
        except ValueError:
            privilege = 0
        new_crossproc['privileges'] = _lookup_privilege(privilege)
        new_crossproc['privilege_code'] = privilege

        new_crossproc['tamper_flag'] = False
        if parts[7] == 'true':
            new_crossproc['tamper_flag'] = True

        new_crossproc['is_target'] = False
        if len(parts) > 7:
            if parts[8] == 'true':
                new_crossproc['is_target'] = True

        if new_crossproc['is_target'] == True:
            new_crossproc['target_procguid'] = self.process_model.id
            new_crossproc['target_md5'] = self.process_model.process_md5
            new_crossproc['target_path'] = self.process_model.path
            new_crossproc['source_procguid'] = parts[2]
            new_crossproc['source_md5'] = parts[3]
            new_crossproc['source_path'] = parts[4]
        else:
            new_crossproc['target_procguid'] = parts[2]
            new_crossproc['target_md5'] = parts[3]
            new_crossproc['target_path'] = parts[4]
            new_crossproc['source_procguid'] = self.process_model.id
            new_crossproc['source_md5'] = self.process_model.process_md5
            new_crossproc['source_path'] = self.process_model.path

        return CbCrossProcEvent(self.process_model, timestamp, seq, new_crossproc)


class ProcessV2Parser(ProcessV1Parser):
    def __init__(self, process_model):
        super(ProcessV2Parser, self).__init__(process_model)

    def parse_netconn(self, seq, netconn):
        new_conn = {}
        timestamp = convert_event_time(netconn.get("timestamp", None))
        direction = netconn.get("direction", "true")

        if direction == 'true':
            new_conn['direction'] = 'Outbound'
        else:
            new_conn['direction'] = 'Inbound'

        for ipfield in ('remote_ip', 'local_ip', 'proxy_ip'):
            try:
                new_conn[ipfield] = socket.inet_ntoa(struct.pack('>i', int(netconn.get(ipfield, 0))))
            except:
                new_conn[ipfield] = netconn.get(ipfield, '0.0.0.0')

        for portfield in ('remote_port', 'local_port', 'proxy_port'):
            new_conn[portfield] = int(netconn.get(portfield, 0))

        new_conn['proto'] = protocols.get(int(netconn.get('proto', 0)), "Unknown")
        new_conn['domain'] = netconn.get('domain', '')

        return CbNetConnEvent(self.process_model, timestamp, seq, new_conn, version=2)


class Process(TaggedModel):
    urlobject = '/api/v1/process'
    default_sort = 'last_update desc'

    @classmethod
    def new_object(cls, cb, item):
        # TODO: do we ever need to evaluate item['unique_id'] which is the id + segment id?
        # TODO: is there a better way to handle this? (see how this is called from Query._search())
        return cb.select(Process, item['id'], long(item['segment_id']), initial_data=item)

    def __init__(self, cb, procguid, segment=None, initial_data=None, force_init=False):
        self.segment = segment
        try:
            # old 4.x process IDs are integers.
            self.id = int(procguid)
        except ValueError:
            # new 5.x process IDs are hex strings with optional segment IDs.
            if len(procguid) == 36:
                self.id = procguid
            elif len(procguid) == 45:
                self.id = procguid[:36]
                self.segment = int(procguid[38:], 16)

        if not self.segment:
            self.segment = 1

        super(Process, self).__init__(cb, "%s-%08x" % (self.id, self.segment))

        if cb.cb_server_version >= LooseVersion('5.1.0'):
            # CbER 5.1.0 introduced an extended event API
            self._process_event_api = 'v2'
            self._event_parser = ProcessV2Parser(self)
        else:
            self._process_event_api = 'v1'
            self._event_parser = ProcessV1Parser(self)

        if initial_data:
            # fill in data object for performance
            self._info = dict(initial_data)

        if force_init:
            self.refresh()

    def _build_api_request_uri(self):
        # TODO: how do we handle process segments?
        return "/api/{0}/process/{1}/{2}/event".format(self._process_event_api, self.id, self.segment)

    def _parse(self, obj):
        self._info = obj.get('process', {})

    def walk_parents(self, callback, max_depth=0, depth=0):
        if max_depth and depth > max_depth:
            return

        try:
            parent_proc = self.parent
        except:
            return
        else:
            # TODO: this is a crude hack to find a "valid" process.
            # We should investigate a better way of doing this.
            if getattr(parent_proc, 'process_pid', None):
                callback(parent_proc, depth=depth)
                parent_proc.walk_parents(callback, max_depth=max_depth, depth=depth+1)

    def walk_children(self, callback, max_depth=0, depth=0):
        if max_depth and depth > max_depth:
            return

        for cpevent in self.children:
            if not cpevent.terminated:
                try:
                    proc = cpevent.process
                except:
                    continue
                else:
                    # TODO: this is a crude hack to find a "valid" process.
                    # We should investigate a better way of doing this.
                    if getattr(proc, 'process_pid', None):
                        callback(proc, depth=depth)
                        proc.walk_children(callback, max_depth=max_depth, depth=depth+1)

    @property
    def start(self):
        return convert_from_solr(self._attribute('start', -1))

    @property
    def modloads(self):
        """Generator that returns `:py:class:CbModLoadEvent` associated with this process"""
        i = 0
        for raw_modload in self._attribute('modload_complete', []):
            yield self._event_parser.parse_modload(i, raw_modload)
            i += 1

    @property
    def unsigned_modloads(self):
        return [m for m in self.modloads if not m.is_signed]

    @property
    def filemods(self):
        """Generator that returns :py:class:`CbFileModEvent` objects associated with this process"""
        i = 0
        for raw_filemod in self._attribute('filemod_complete', []):
            yield self._event_parser.parse_filemod(i, raw_filemod)
            i += 1

    @property
    def netconns(self):
        """Generator that returns :py:class:`CbNetConnEvent` objects associated with this process"""
        i = 0
        for raw_netconn in self._attribute('netconn_complete', []):
            yield self._event_parser.parse_netconn(i, raw_netconn)
            i += 1

    @property
    def regmods(self):
        """Generator that returns :py:class:`CbRegModEvent` objects associated with this process"""
        i = 0
        for raw_regmod in self._attribute('regmod_complete', []):
            yield self._event_parser.parse_regmod(i, raw_regmod)
            i += 1

    @property
    def crossprocs(self):
        """Generator that returns :py:class:`CbCrossProcEvent` objects associated with this process"""
        i = 0
        for raw_crossproc in self._attribute('crossproc_complete', []):
            yield self._event_parser.parse_crossproc(i, raw_crossproc)
            i += 1

    @property
    def children(self):
        """Generator that returns :py:class:`CbChildProcEvent` objects associated with this process"""
        i = 0
        for raw_childproc in self._attribute('childproc_complete', []):
            yield self._event_parser.parse_childproc(i, raw_childproc)
            i += 1

    @property
    def all_events(self):
        """Returns a list of all events associated with this process, sorted by timestamp"""
        return sorted(list(self.modloads) + list(self.netconns) + list(self.filemods) + \
                      list(self.children) + list(self.regmods) + list(self.crossprocs))

    @property
    def tamper_events(self):
        return [e for e in self.all_events if e.tamper_event]

    def find_file_writes(self, filename):
        return [filemod for filemod in self.filemods if filemod.path == filename]

    @property
    def binary(self):
        binary_md5 = self.get('process_md5')
        if binary_md5:
            return self._cb.select(Binary, binary_md5)
        else:
            return None

    @property
    def comms_ip(self):
        return socket.inet_ntoa(struct.pack('>i', self._attribute('comms_ip', 0)))

    @property
    def parent(self):
        parent_unique_id = self.get('parent_unique_id', None)
        parent_id = self.get('parent_id', None)

        if parent_unique_id:
            return self._cb.select(self.__class__, self.get_correct_unique_id(parent_id, parent_unique_id), 1)
        elif parent_id:
            return self._cb.select(self.__class__, parent_id, 1)
        else:
            return None  # no parent, top of the tree

    @property
    def cmdline(self):
        cmdline = self.get('cmdline')
        if not cmdline:
            return self.path
        else:
            return cmdline

    @property
    def sensor(self):
        sensor_id = self.get("sensor_id")
        if sensor_id:
            return self._cb.select(Sensor, int(sensor_id))
        else:
            return None

    @property
    def webui_link(self):
        return '%s/#analyze/%s/%s' % (self._cb.url, self.id, self.segment)

    def get_correct_unique_id(self, old_style_id, new_style_id):
        # this is required for the new 4.2 style GUIDs...
        (sensor_id, proc_pid, proc_createtime) = parse_42_guid(new_style_id)
        if sensor_id != self.sensor.id:
            return old_style_id
        else:
            return new_style_id

    @property
    def last_update(self):
        return convert_from_solr(self.get('last_update', -1))

    @property
    def username(self):
        return self.get("username", None)


def get_constants(prefix):
    return dict((getattr(socket, n), n)
                for n in dir(socket)
                if n.startswith(prefix)
    )


protocols = get_constants("IPPROTO_")


windows_rights_dict = {
    0x00100000: 'SYNCHRONIZE',
    0x00080000: 'WRITE_OWNER',
    0x00040000: 'WRITE_DAC',
    0x00020000: 'READ_CONTROL',
    0x00010000: 'DELETE',
    0x00000001: 'PROCESS_TERMINATE',
    0x00000002: 'PROCESS_CREATE_THREAD',
    0x00000004: 'PROCESS_SET_SESSIONID',
    0x00000008: 'PROCESS_VM_OPERATION',
    0x00000010: 'PROCESS_VM_READ',
    0x00000020: 'PROCESS_VM_WRITE',
    0x00000040: 'PROCESS_DUP_HANDLE',
    0x00000080: 'PROCESS_CREATE_PROCESS',
    0x00000100: 'PROCESS_SET_QUOTA',
    0x00000200: 'PROCESS_SET_INFORMATION',
    0x00000400: 'PROCESS_QUERY_INFORMATION',
    0x00000800: 'PROCESS_SUPEND_RESUME',
    0x00001000: 'PROCESS_QUERY_LIMITED_INFORMATION'
}
r_windows_rights_dict = dict((value, key) for key, value in iteritems(windows_rights_dict))


@total_ordering
@python_2_unicode_compatible
class CbEvent(object):
    def __init__(self, parent_process, timestamp, sequence, event_data):
        self.timestamp = timestamp
        self.parent = parent_process
        self.sequence = sequence
        self.__dict__.update(event_data)

        self.event_type = u'Generic Cb event'
        self.stat_titles = ['timestamp']

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __str__(self):
        ret = '%s:\n' % self.event_type
        ret += u'\n'.join(['%-20s : %s' %
                           (a, getattr(self, a, "")) for a in self.stat_titles])

        return ret

    @property
    def tamper_event(self):
        return getattr(self, "tamper_flag", False)


class CbModLoadEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data, binary_data=None):
        super(CbModLoadEvent,self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Module Load event'
        self.stat_titles.extend(['md5', 'path'])

        self.binary_data = binary_data

    @property
    def binary(self):
        return self.parent._cb.select(Binary, self.md5, initial_data=self.binary_data)

    @property
    def is_signed(self):
        return self.binary.signed


class CbFileModEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data):
        super(CbFileModEvent,self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb File Modification event'
        self.stat_titles.extend(['type', 'path', 'filetype', 'md5'])


class CbRegModEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data):
        super(CbRegModEvent,self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Registry Modification event'
        self.stat_titles.extend(['type', 'path'])


class CbNetConnEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data, version=1):
        super(CbNetConnEvent,self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Network Connection event'
        self.stat_titles.extend(['domain', 'remote_ip', 'remote_port', 'proto', 'direction'])
        if version == 2:
            self.stat_titles.extend(['local_ip', 'local_port', 'proxy_ip', 'proxy_port'])


class CbChildProcEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data):
        super(CbChildProcEvent,self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Child Process event'
        self.stat_titles.extend(['procguid', 'pid', 'path', 'md5'])

    @property
    def process(self):
        return self.parent._cb.select(Process, self.procguid, 1)


class CbCrossProcEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data):
        super(CbCrossProcEvent,self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Cross Process event'
        self.stat_titles.extend(['type', 'privileges', 'target_md5', 'target_path'])

    @property
    def target_proc(self):

        return self.parent._cb.select(Process, self.target_procguid)

    @property
    def source_proc(self):
        return self.parent._cb.select(Process, self.source_procguid)

    def has_permission(self, perm):
        if perm in r_windows_rights_dict:
            if (self.privilege_code & r_windows_rights_dict[perm]) == r_windows_rights_dict[perm]:
                return True
            else:
                return False
        raise KeyError(perm)

    def has_permissions(self, perms):
        for perm in perms:
            if not self.has_permission(perm):
                return False
        return True
