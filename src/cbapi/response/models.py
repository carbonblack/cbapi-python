#!/usr/bin/env python
from __future__ import absolute_import

import copy
import json
from distutils.version import LooseVersion
from collections import namedtuple, defaultdict
import base64
from datetime import datetime, timedelta
from zipfile import ZipFile
from contextlib import closing
import struct
from cbapi.six.moves import urllib
from copy import deepcopy
import cbapi.six as six
import logging
import time

from itertools import chain
from cbapi.utils import convert_query_params
from ..errors import InvalidObjectError, ApiError, TimeoutError
from ..oldmodels import BaseModel, immutable

from ..models import NewBaseModel, MutableBaseModel, CreatableModelMixin
from .utils import convert_from_cb, convert_from_solr, parse_42_guid, convert_event_time, parse_process_guid, \
    convert_to_solr
from ..errors import ServerError, InvalidHashError, ObjectNotFoundError
from ..query import SimpleQuery, PaginatedQuery
from .query import Query

from cbapi.six import python_2_unicode_compatible, iteritems

# Get constants for decoding the Netconn events
import socket

if six.PY3:
    long = int
    from io import BytesIO as StringIO
else:
    from cStringIO import StringIO

try:
    from functools import total_ordering
except ImportError:
    from total_ordering import total_ordering


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


class IngressFilter(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/v1/ingress_whitelist"
    swagger_meta_file = "response/models/ingress_filter.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    def _update_object(self):
        # when creating a new IngressFilter, we must send it as an array of one:
        if self.__class__.primary_key in self._dirty_attributes.keys() or self._model_unique_id is None:
            log.debug("Creating a new {0:s} object".format(self.__class__.__name__))
            ret = self._cb.api_json_request(self.__class__._new_object_http_method, self.urlobject,
                                            data=[self._info])
            ids = ret.json()
            self.id = ids[0]
            self._dirty_attributes = {}
            self.refresh()
            return self.id
        else:
            log.debug("Updating {0:s} with unique ID {1:s}".format(self.__class__.__name__, str(self._model_unique_id)))
            ret = self._cb.api_json_request(self.__class__._change_object_http_method,
                                            self._build_api_request_uri(), data=self._info)
            return self._refresh_if_needed(ret)


class StoragePartitionQuery(SimpleQuery):
    @property
    def results(self):
        if not self._full_init:
            self._results = []
            for k, v in iteritems(self._cb.get_object(self._urlobject, default={})):
                t = self._doc_class.new_object(self._cb, v, full_doc=True)
                if self._match_query(t):
                    self._results.append(t)
            self._results = self._sort(self._results)
            self._full_init = True

        return self._results


class StoragePartition(NewBaseModel):
    """
    The StoragePartition model object allows you to load and unload Time Paritioning "cores" into the Cb Response server
    through the API. This model is only available in Cb Response server versions 6.0 and above.
    Cb Response will roll-over data into new Solr partition periodically (based on configuration) in order to improve
    performance and data retention.

    Partitions can be:

    Hot: There is always exactly one hot partition. It is called "writer" (configurable).
    All new data goes to the writer partition. Hot partition can be searched.

    Warm: Warm partition is any mounted partition that is not currently written to. Warm partitions can be searched.
    Warm partition are named as "cbevents_<timestmp>" where timestamp is time when partition was created in format
    "YYYY_MM_DD_hhmm". Timestamp can be followed by suffix in format "_<suffix>" which will be ignored and can be used
    to specify additional partition information. Here are examples of valid partition names:
    cbevents_2016_06_11_1351
    cbevents_2016_06_11_1351_foo
    cbevents_2016_06_11_1351_this_is_partition_from_old_server

    Cold: Cold partition is any partition that is not mounted to Solr, but exists only on disk. Cold partitions can not
    be searched, but can be mounted (converted into warm partitions)

    Deleted: Deleted partition is removed from disk and can no longer be looked up or restored
    """
    urlobject = "/api/v1/storage/events/partition"
    primary_key = "name"

    @classmethod
    def _query_implementation(cls, cb):
        return StoragePartitionQuery(cls, cb)

    def _refresh(self):
        # there is no GET method for a StoragePartition.
        return True

    def delete(self):
        self._cb.delete_object("/api/v1/storage/events/{0}".format(self._model_unique_id))

    def unmount(self):
        self._cb.post_object("/api/v1/storage/events/{0}/unmount".format(self._model_unique_id), None)

    def mount(self):
        self._cb.post_object("/api/v1/storage/events/{0}/mount".format(self._model_unique_id), None)


class BannedHash(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/v1/banning/blacklist"
    swagger_meta_file = "response/models/hash_blacklist.yaml"
    primary_key = "md5hash"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb, urlobject=BannedHash.urlobject + "?count=10000")

    @property
    def binary(self):
        """
        Joins this attribute with the :class:`.Binary` object associated with this Banned Hash object
        """
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
class ThrottleRule(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/throttle"
    swagger_meta_file = "response/models/throttle.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb)

    @property
    def site(self):
        return self._join(Site, "site_id")


class AlertQuery(Query):
    def __init__(self, doc_class, cb, query=None, raw_query=None):
        super(AlertQuery, self).__init__(doc_class, cb, query=query, raw_query=raw_query)
        self._batch_size = 500

    def _bulk_update(self, payload):
        # Using IDs for Alerts, since queries don't quite work as planned, and an "empty" query doesn't work.
        alert_ids = [a["unique_id"] for a in self._search()]

        # Send the updates in blocks of 500
        block_size = 500
        cur, left = alert_ids[:block_size], alert_ids[block_size:]
        while cur:
            payload["alert_ids"] = cur
            cur, left = left[:block_size], left[block_size:]
            self._cb.post_object("/api/v1/alerts", payload)

        return None

    def set_ignored(self, ignored_flag=True):
        payload = {"updates": {"is_ignored": ignored_flag, "requested_status": "False Positive"}}
        return self._bulk_update(payload)

    def assign(self, target):
        payload = {"assigned_to": target, "requested_status": "In Progress"}
        return self._bulk_update(payload)

    def change_status(self, new_status):
        payload = {"requested_status": new_status}
        return self._bulk_update(payload)


class Alert(MutableBaseModel):
    urlobject = "/api/v2/alert"
    swagger_meta_file = "response/models/alert.yaml"
    _change_object_http_method = "POST"
    primary_key = "unique_id"

    @classmethod
    def _query_implementation(cls, cb):
        return AlertQuery(cls, cb)

    def __init__(self, cb, alert_id, initial_data=None):
        super(Alert, self).__init__(cb, alert_id, initial_data)

    def _refresh(self):
        # there is no GET method for an Alert.
        return True

    @property
    def process(self):
        if 'process' in self.alert_type:
            # there is a bug in Cb Response 6.1.x where segment_ids in alerts are truncated, so instead
            # we will just select the process by its process_id.
            return self._cb.select(Process, self.process_id)
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
        """
        Perform a *Process* search within this feed that satisfies min_score and max_score

        :param min_score: minimum feed score
        :param max_score: maximum feed score
        :return: Returns a :py:class:`response.rest_api.Query` object with the appropriate
            search parameters for processes
        :rtype: :py:class:`response.rest_api.Query`
        """
        return self._search(Process, min_score, max_score)

    def search_binaries(self, min_score=None, max_score=None):
        """
        Perform a *Binary* search within this feed that satisfies min_score and max_score
        :param min_score: minimum feed score
        :param max_score: maximum feed score
        :return: Returns a :py:class:`response.rest_api.Query` object within the appropriate
            search parameters for binaries
        :rtype: :py:class:`response.rest_api.Query`
        """
        return self._search(Binary, min_score, max_score)

    @property
    def actions(self):
        """
        :return: Returns all :class:`.FeedAction` objects associated with this feed
        :rtype: :py:class:`response.rest_api.Query`
        """
        return self._cb.select(FeedAction).where("group_id:{0}".format(int(self._model_unique_id)))

    @property
    def reports(self):
        return self._cb.select(ThreatReport).where("feed_id:{0}".format(int(self._model_unique_id)))

    def create_action(self):
        new_action = self._cb.create(FeedAction)
        new_action.group_id = int(self._model_unique_id)
        # Cb Response requires the watchlist_id field to be filled in; the UI uses -1 for this
        new_action.watchlist_id = -1
        return new_action

    def synchronize(self, full_sync=True):
        try:
            self._cb.post_object("/api/v1/feed/{0}/synchronize".format(self._model_unique_id),
                                 {"full_sync": full_sync})
        except ServerError as e:
            if e.error_code == 409:
                raise ApiError("Cannot synchronize feed {0}: feed is disabled".format(self._model_unique_id))
            else:
                raise


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


class SensorPaginatedQuery(PaginatedQuery):
    valid_field_names = ['ip', 'hostname', 'groupid']

    def __init__(self, doc_class, cb, query=None):
        super(SensorPaginatedQuery, self).__init__(doc_class, cb, query)
        if not self._query:
            self._query = {}

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        nq._query = self._query
        nq._batch_size = self._batch_size
        return nq

    def where(self, new_query):
        if self._query:
            raise ApiError("Cannot have multiple 'where' clauses")

        nq = self._clone()
        field, value = new_query.split(':', 1)
        nq._query = {}
        nq._query[field] = value
        nq._full_init = False

        for k, v in iteritems(nq._query):
            if k not in SensorQuery.valid_field_names:
                nq._query = {}
                raise ValueError("Field name must be one of: {0:s}".format(", ".join(SensorQuery.valid_field_names)))

        return nq

    def _count(self):
        if self._count_valid:
            return self._total_results

        if self._query:
            args = self._query.copy()
        else:
            args = {}

        args['start'] = 0
        args['rows'] = 0

        qargs = convert_query_params(args)

        self._total_results = self._cb.get_object("/api/v2/sensor", query_parameters=qargs).get('total_results', 0)

        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0):
        # iterate over total result set, 100 at a time

        if self._query:
            args = self._query.copy()
        else:
            args = {}

        args['start'] = start

        if rows:
            args['rows'] = min(rows, self._batch_size)
        else:
            args['rows'] = self._batch_size

        still_querying = True
        current = start
        numrows = 0

        while still_querying:
            qargs = convert_query_params(args)
            result = self._cb.get_object("/api/v2/sensor", query_parameters=qargs)

            self._total_results = result.get('total_results')
            self._count_valid = True

            for item in result.get('results'):
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current

            if current >= self._total_results:
                break

    def facets(self, *args):
        """Retrieve a dictionary with the facets for this query.

        :param args: Any number of fields to use as facets
        :return: Facet data
        :rtype: dict
        """

        qargs = self._query.copy()
        qargs['facet'] = 'true'
        qargs['start'] = 0
        qargs['rows'] = 100       # TODO: unlike solr, we need to actually retrieve the results to calculate the facets.
        qargs['facet.field'] = list(args)

        if self._query:
            qargs['q'] = self._query

        query_params = convert_query_params(qargs)
        return self._cb.get_object("/api/v2/sensor", query_parameters=query_params).get('facets', {})


class Sensor(MutableBaseModel):
    swagger_meta_file = "response/models/sensorObject.yaml"
    urlobject = '/api/v1/sensor'
    NetworkAdapter = namedtuple('NetworkAdapter', ['macaddr', 'ipaddr'])

    def __init__(self, *args, **kwargs):
        super(Sensor, self).__init__(*args, **kwargs)

    @classmethod
    def _query_implementation(cls, cb):
        # ** Disable the paginated query implementation for now **

        # if cb.cb_server_version >= LooseVersion("5.2.0"):
        #     return SensorPaginatedQuery(cls, cb)
        # else:
        #     return SensorQuery(cls, cb)
        return SensorQuery(cls, cb)

    @property
    def group(self):
        """
        :getter:

        Returns the sensor's group id.

        :setter:

        Allows access to set the sensor's group id
        """
        return self._join(SensorGroup, "group_id")

    @group.setter
    def group(self, new_group):
        self.group_id = new_group.id

    @property
    def dns_name(self):
        """
        Returns the DNS name associated with this sensor object.  This is the same as 'computer_dns_name'.
        """
        return getattr(self, 'computer_dns_name', None)

    @property
    def hostname(self):
        """
        Returns the hostname associated with this sensor object.  This is the same as 'computer_name'
        """
        return getattr(self, 'computer_name', None)

    @property
    def network_interfaces(self):
        """
        Returns a list of networks adapters on the sensor
        """
        out = []
        for adapter in getattr(self, 'network_adapters', '').split('|'):
            parts = adapter.split(',')
            if len(parts) == 2:
                out.append(Sensor.NetworkAdapter._make([':'.join(a+b for a, b in zip(parts[1][::2], parts[1][1::2])),
                                                        parts[0]]))
        return out

    @property
    def os(self):
        """
        Returns the operating system display string of the sensor
        """
        return getattr(self, 'os_environment_display_string', None)

    @property
    def registration_time(self):
        """
        Returns the time the sensor registered with the Cb Response Server
        """
        return convert_from_cb(getattr(self, 'registration_time', -1))

    @property
    def sid(self):
        """
        Security Identifier being used by the Cb Response Sensor
        """
        return getattr(self, 'computer_sid')

    @property
    def webui_link(self):
        """
        Returns the Cb Response Web UI link associated with this Sensor
        """
        return '{0:s}/#/host/{1}'.format(self._cb.url, self._model_unique_id)

    # TODO: properly handle the stats api routes
    @property
    def queued_stats(self):
        """
        Returns a list of status and size of the queued event logs from the associated Cb Response Sensor

        :example:

        >>> sensor_obj = c.select(Sensor).where("ip:192.168").first()
        >>> pprint.pprint(sensor_obj.queued_stats)
        [{u'id': u'355509',
          u'num_eventlog_bytes': u'0',
          u'num_eventlogs': u'0',
          u'num_storefile_bytes': u'0',
          u'num_storefiles': 0,
          u'sensor_id': 1,
          u'timestamp': u'2016-10-17 19:08:09.645294-05:00'}]
        """
        return self._cb.get_object("{0}/queued".format(self._build_api_request_uri()), default=[])

    @property
    def activity_stats(self):
        """
        Returns a list of activity statistics from the associated Cb Response Sensor
        """
        return self._cb.get_object("{0}/activity".format(self._build_api_request_uri()), default=[])

    @property
    def resource_status(self):
        """
        Returns a list of memory statistics used by the Cb Response Sensor
        """
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
        """
        Performs a flush of events for this Cb Response Sensor

        :warning: This may cause a significant amount of network traffic from this sensor to the Cb Response Server
        """

        # Note that Cb Response 6 requires the date/time stamp to be sent in RFC822 format (not ISO 8601).
        # since the date/time stamp just needs to be far in the future, we just fake a GMT timezone.
        self.event_log_flush_time = datetime.now() + timedelta(days=365)
        self.save()

    def restart_sensor(self):
        """
        Restarts the Carbon Black sensor (*not* the underlying endpoint operating system).

        This simply sets the flag to ask the sensor to restart the next time it checks into the Cb Response server,
        it does not wait for the sensor to restart.
        """
        self.restart_queued = True
        self.save()

    def isolate(self, timeout=None):
        """
        Turn on network isolation for this Cb Response Sensor.

        This function will block and only return when the isolation is complete, or if a timeout is reached. By default,
        there is no timeout. You can specify a timeout period (in seconds) in the "timeout" parameter to this
        function. If a timeout is specified and reached before the sensor is confirmed isolated, then this function
        will throw a TimeoutError.

        :return: True if sensor is isolated
        :raises TimeoutError: if sensor does not isolate before timeout is reached
        """
        self.network_isolation_enabled = True
        self.save()

        start_time = time.time()

        while not self.is_isolating:
            if timeout and time.time() - start_time > timeout:
                raise TimeoutError(message="timed out waiting for isolation to become active")
            time.sleep(1)
            self.refresh()

        return True

    def unisolate(self, timeout=None):
        """
        Turn off network isolation for this Cb Response Sensor.

        This function will block and only return when the isolation is removed, or if a timeout is reached. By default,
        there is no timeout. You can specify a timeout period (in seconds) in the "timeout" parameter to this
        function. If a timeout is specified and reached before the sensor is confirmed unisolated, then this function
        will throw a TimeoutError.

        :return: True if sensor is unisolated
        :raises TimeoutError: if sensor does not unisolate before timeout is reached
        """
        self.network_isolation_enabled = False
        self.save()

        start_time = time.time()

        while self.is_isolating:
            if timeout and time.time() - start_time > timeout:
                raise TimeoutError(message="timed out waiting for isolation to be removed")
            time.sleep(1)
            self.refresh()

        return True

    def _update_object(self):
        # Workarounds for issuing a sensor queue flush in Cb Response 6.0
        # - We only want to reflect back the event_log_flush_time if the user explicitly set it to a new value
        #   (therefore, set the event_log_flush_time to None if it isn't marked dirty)
        # - The event_log_flush_time must be sent in RFC822 format (not ISO 8601) for Cb Response 6.x servers.
        #
        # Note that even though we delete the event_log_flush_time here, it'll get re-initialized when we GET
        #  the sensor after sending the PUT request.
        if "event_log_flush_time" in self._dirty_attributes and self._info.get("event_log_flush_time",
                                                                               None) is not None:
            if self._cb.cb_server_version > LooseVersion("6.0.0"):
                # since the date/time stamp just needs to be far in the future, we just fake a GMT timezone.
                try:
                    self._info["event_log_flush_time"] = self.event_log_flush_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
                except Exception:
                    log.debug("Could not parse event_log_flush_time in the Sensor object, setting it to None.")
                    self._info["event_log_flush_time"] = None
        else:
            self._info["event_log_flush_time"] = None

        return super(Sensor, self)._update_object()


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
    _multiple_where_clauses_accepted = True

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
            # ZE CB-15681 - REMOVE BLOCK WHEN BUG IS FIXED
            try:
                full_results = self._cb.get_object(self._urlobject, query_parameters=convert_query_params(self._query))
            except ServerError:
                full_results = False
            # ZE CB-15681 - REMOVE BLOCK WHEN BUG IS FIXED
            if not full_results:
                self._results = []
            else:
                self._results = [self._doc_class.new_object(self._cb, it, full_doc=True) for it in full_results]
            self._results = self._sort(self._results)
            self._full_init = True

        return self._results


class Team(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/team.yaml"
    urlobject = "/api/team"

    @classmethod
    def _query_implementation(cls, cb):
        return SimpleQuery(cls, cb, urlobject="/api/teams", returns_fulldoc=False)

    def _add_access(self, sg, access_type):
        if isinstance(sg, int):
            sg = self._cb.select(SensorGroup, sg)

        new_access = [ga for ga in self.group_access if ga.get("group_id") != sg.id]
        new_access.append({
            "group_id": sg.id,
            "access_category": access_type,
            "group_name": sg.name
        })
        self.group_access = new_access

    def add_viewer_access(self, sg):
        return self._add_access(sg, "Viewer")

    def add_administrator_access(self, sg):
        return self._add_access(sg, "Administrator")


class User(MutableBaseModel, CreatableModelMixin):
    swagger_meta_file = "response/models/user.yaml"
    urlobject = "/api/user"
    primary_key = "username"
    _new_object_needs_primary_key = True

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

    def _update_object(self):
        if self._cb.cb_server_version < LooseVersion("6.1.0") or self._info.get("id", None) is None:
            # only include IDs of the teams and not the entire dictionary
            # - applies to Cb Response server < 6.0 as well as Cb Response servers >= 6.0 where the user hasn't
            #   been created yet.
            if self.__class__.primary_key in self._dirty_attributes.keys() or self._model_unique_id is None:
                new_object_info = deepcopy(self._info)
                try:
                    del(new_object_info["id"])
                except KeyError:
                    pass
                new_teams = [t.get("id") for t in new_object_info["teams"]]
                new_teams = [t for t in new_teams if t]
                new_object_info["teams"] = new_teams

                try:
                    if not self._new_object_needs_primary_key:
                        del (new_object_info[self.__class__.primary_key])
                except Exception:
                    pass
                log.debug("Creating a new {0:s} object".format(self.__class__.__name__))
                ret = self._cb.api_json_request(self.__class__._new_object_http_method, self.urlobject,
                                                data=new_object_info)
            else:
                log.debug(
                    "Updating {0:s} with unique ID {1:s}".format(self.__class__.__name__, str(self._model_unique_id)))
                ret = self._cb.api_json_request(self.__class__._change_object_http_method,
                                                self._build_api_request_uri(), data=self._info)

            return self._refresh_if_needed(ret)
        else:
            return super(User, self)._update_object()

    def add_team(self, t):
        if isinstance(t, int):
            t = self._cb.select(Team, t)
        elif type(t) in six.string_types:
            t = self._cb.select(Team).where("name:%s" % t).one()

        new_teams = [team for team in self.teams if team.get("id") != t.id]
        new_teams.append({"id": t.id, "name": t.name})
        self.teams = new_teams

    def remove_team(self, t):
        if isinstance(t, int):
            t = self._cb.select(Team, t)
        elif type(t) in six.string_types:
            t = self._cb.select(Team).where("name:%s" % t).one()

        new_teams = []
        for team in self.teams:
            keep = True
            if isinstance(team, int):
                if team == t.id:
                    keep = False
            elif isinstance(team, dict):
                if team.get("id") == t.id:
                    keep = False

            if keep:
                new_teams.append(team)

        self.teams = new_teams


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
        """
        :getter:

        Returns the query associated with this watchlist.

        :setter:

        Allows access to set the query associated with this watchlist
        """
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
        self.search_query = "&".join(("{0}={1}".format(k, urllib.parse.quote(v)) for k, v in qt))

    @property
    def facets(self):
        """
        Returns facets from the search associated with the watchlist query

        :return: dictionary of facets as keys
        :rtype: dict
        """
        facets = {}
        for k, v in self._query:
            if k.startswith("cb.fq."):
                facets[k[6:]] = v

        return facets

    def search(self):
        """
        Creates a search based on the watchlist's search parameter

        :return: a `Process` :py:class:`.response.rest_api.Query` or Binary :py:class:`.response.rest_api.Query`
        :rtype: :py:class:`.response.rest_api.Query`
        """
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
        process_segment = getattr(self, "segment_id", None)
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


class ThreatReportQuery(Query):
    def set_ignored(self, ignored_flag=True):
        qt = (("cb.urlver", "1"), ("q", self._query))
        search_query = "&".join(("{0}={1}".format(k, urllib.parse.quote(v)) for k, v in qt))

        payload = {"updates": {"is_ignored": ignored_flag}, "query": search_query}
        self._cb.post_object("/api/v1/threat_report", payload)


class ThreatReport(MutableBaseModel):
    urlobject = '/api/v1/threat_report'
    primary_key = "_internal_id"

    @classmethod
    def _query_implementation(cls, cb):
        if cb.cb_server_version >= LooseVersion('5.1.0'):
            return ThreatReportQuery(cls, cb)
        else:
            return Query(cls, cb)

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
                initial_data = {"feed_id": feed_id, "id": report_id}
            except Exception:
                raise ApiError("ThreatReport ID must be in form '<feed_id>:<report_id>'")

        super(ThreatReport, self).__init__(cb, full_id, initial_data)

    @property
    def feed(self):
        return self._join(Feed, "feed_id")

    def _update_object(self):
        update_content = {"ids": {str(self.feed_id): [str(self.id)]}, "updates": {}}
        for k in self._dirty_attributes.keys():
            update_content["updates"][k] = getattr(self, k)

        ret = self._cb.post_object(ThreatReport.urlobject, update_content)

        if ret.status_code not in (200, 204):
            try:
                message = json.loads(ret.text)[0]
            except Exception:
                message = ret.text

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
                    self._info = json.loads(ret.text)
                    self._full_init = True
            except Exception:
                self.refresh()

        self._dirty_attributes = {}
        return self._model_unique_id


class WatchlistEnabledQuery(Query):
    def create_watchlist(self, watchlist_name):
        """Create a watchlist based on this query.

        :param str watchlist_name: name of the new watchlist
        :return: new Watchlist object
        :rtype: :py:class:`Watchlist`
        """
        if self._raw_query:
            args = self._raw_query.copy()
        else:
            args = self._default_args.copy()

            if self._query:
                args['q'] = self._query
            else:
                args['q'] = ''

        if self._sort_by:
            args['sort'] = self._sort_by

        new_watchlist = self._cb.create(Watchlist, data={"name": watchlist_name})
        new_watchlist.search_query = urllib.parse.urlencode(args)
        if self._doc_class == Binary:
            new_watchlist.index_type = "modules"
        else:
            new_watchlist.index_type = "events"

        return new_watchlist.save()


class ProcessQuery(WatchlistEnabledQuery):
    def __init__(self, doc_class, cb, query=None, raw_query=None):
        super(ProcessQuery, self).__init__(doc_class, cb, query, raw_query)
        self.num_children = 15
        if cb._has_legacy_partitions:
            self._default_args["cb.legacy_5x_mode"] = True

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb, self._query, self._raw_query)
        nq._default_args = copy.deepcopy(self._default_args)
        nq.num_children = self.num_children
        nq._batch_size = self._batch_size
        nq._sort_by = self._sort_by
        return nq

    def group_by(self, field_name):
        """Set the group-by field name for this query. Typically, you will want to set this to 'id' if you only want
        one result per process.

        This method is only available for Cb Response servers 6.0 and above. Calling this on a Query object connected
        to a Cb Response 5.x server will simply result in a no-op.

        :param str field_name: Field name to group the result set by.
        :return: Query object
        :rtype: :py:class:`ProcessQuery`
        """
        if self._cb.cb_server_version >= LooseVersion('6.0.0'):
            nq = self._clone()
            nq._default_args["cb.group"] = field_name
            return nq
        else:
            log.debug("group_by only supported in Cb Response 6.1+")
            return self

    def max_children(self, num_children):
        """Sets the number of children to fetch with the process

        This method is only available for Cb Response servers 6.0 and above. Calling this on a Query object connected
        to a Cb Response 5.x server will simply result in a no-op.

        :default: 15
        :param int num_children: Number of children to fetch with process
        :return: Query object
        :rtype: :py:class:`ProcessQuery`
        """
        nq = self._clone()
        try:
            num_children = int(num_children)
        except ValueError:
            num_children = 15

        nq.num_children = num_children
        return nq

    def _perform_query(self, start=0, numrows=0):
        for item in self._search(start=start, rows=numrows):
            yield self._doc_class.new_object(self._cb, item, self.num_children)

    def set_legacy_mode(self, new_value=True):
        self._default_args["cb.legacy_5x_mode"] = new_value

    def min_last_update(self, v):
        """Set the minimum last update time (relative to sensor) for this query. The timestamp can be expressed either
        as a ``datetime`` like object or as an ISO 8601 string formatted timestamp such as 2017-04-29T04:21:18Z.
        If a ``datetime`` like object is provided, it is assumed to be in GMT time zone.

        This option will limit the number of Solr cores that need to be searched for events that match the query.

        This method is only available for Cb Response servers 6.0 and above. Calling this on a Query object connected
        to a Cb Response 5.x server will simply result in a no-op.

        :param str v: Timestamp (either string or datetime object).
        :return: Query object
        :rtype: :py:class:`ProcessQuery`
        """
        if self._cb.cb_server_version >= LooseVersion('6.0.0'):
            nq = self._clone()
            try:
                v = v.strftime("%Y-%m-%dT%H:%M:%SZ")
            except AttributeError:
                v = str(v)
            nq._default_args["cb.min_last_update"] = v
            return nq
        else:
            log.debug("min_last_update only supported in Cb Response 6.1+")
            return self

    def min_last_server_update(self, v):
        """Set the minimum last update time (relative to server) for this query. The timestamp can be expressed either
        as a ``datetime`` like object or as an ISO 8601 string formatted timestamp such as 2017-04-29T04:21:18Z.
        If a ``datetime`` like object is provided, it is assumed to be in GMT time zone.

        This option will limit the number of Solr cores that need to be searched for events that match the query.

        This method is only available for Cb Response servers 6.0 and above. Calling this on a Query object connected
        to a Cb Response 5.x server will simply result in a no-op.

        :param str v: Timestamp (either string or datetime object).
        :return: Query object
        :rtype: :py:class:`ProcessQuery`
        """
        if self._cb.cb_server_version >= LooseVersion('6.0.0'):
            nq = self._clone()
            try:
                v = v.strftime("%Y-%m-%dT%H:%M:%SZ")
            except AttributeError:
                v = str(v)
            nq._default_args["cb.min_last_server_update"] = v
            return nq
        else:
            log.debug("min_last_server_update only supported in Cb Response 6.1+")
            return self

    def max_last_update(self, v):
        """Set the maximum last update time (relative to sensor) for this query. The timestamp can be expressed either
        as a ``datetime`` like object or as an ISO 8601 string formatted timestamp such as 2017-04-29T04:21:18Z.
        If a ``datetime`` like object is provided, it is assumed to be in GMT time zone.

        This option will limit the number of Solr cores that need to be searched for events that match the query.

        This method is only available for Cb Response servers 6.0 and above. Calling this on a Query object connected
        to a Cb Response 5.x server will simply result in a no-op.

        :param str v: Timestamp (either string or datetime object).
        :return: Query object
        :rtype: :py:class:`ProcessQuery`
        """
        if self._cb.cb_server_version >= LooseVersion('6.0.0'):
            nq = self._clone()
            try:
                v = v.strftime("%Y-%m-%dT%H:%M:%SZ")
            except AttributeError:
                v = str(v)
            nq._default_args["cb.max_last_update"] = v
            return nq
        else:
            log.debug("max_last_update only supported in Cb Response 6.1+")
            return self

    def max_last_server_update(self, v):
        """Set the maximum last update time (relative to server) for this query. The timestamp can be expressed either
        as a ``datetime`` like object or as an ISO 8601 string formatted timestamp such as 2017-04-29T04:21:18Z.
        If a ``datetime`` like object is provided, it is assumed to be in GMT time zone.

        This option will limit the number of Solr cores that need to be searched for events that match the query.

        This method is only available for Cb Response servers 6.0 and above. Calling this on a Query object connected
        to a Cb Response 5.x server will simply result in a no-op.

        :param str v: Timestamp (either string or datetime object).
        :return: Query object
        :rtype: :py:class:`ProcessQuery`
        """
        if self._cb.cb_server_version >= LooseVersion('6.0.0'):
            nq = self._clone()
            try:
                v = v.strftime("%Y-%m-%dT%H:%M:%SZ")
            except AttributeError:
                v = str(v)
            nq._default_args["cb.max_last_server_update"] = v
            return nq
        else:
            log.debug("max_last_server_update only supported in Cb Response 6.1+")
            return self

    def use_comprehensive_search(self):
        """
        Set the `comprehensive_search` flag on the Process query.

        :return: new Query object
        :rtype: :py:class:`ProcessQuery`
        """

        nq = self._clone()
        nq._default_args["comprehensive_search"] = "true"

        return nq


@immutable
class Binary(TaggedModel):

    class SigningData(namedtuple('SigningData', 'result publisher issuer subject sign_time program_name')):
        """
        Class containing binary signing information

        :param str result: Signed or Unsigned
        :param str publisher: Singnature publisher
        :param str issuer: Signature issuer
        :param str subject: Signing subject
        :param str sign_time: Binary signed time
        :param str program_name: Binary program name
        """
        pass

    class VersionInfo(namedtuple('VersionInfo', 'file_desc file_version product_name product_version '
                                                'company_name legal_copyright original_filename')):
        """
        Class containing versioning information about a binary

        :param str file_desc: File description
        :param str file_version: File version
        :param str product_name: Product Name
        :param str product_version: Product version
        :param str company_name: Company Name
        :param str legal_copyright: Copyright
        :param str original_filename: Original File name of this binary
        """
        pass

    class FrequencyData(namedtuple('FrequencyData', 'computer_count process_count all_process_count '
                                                    'module_frequency')):
        """
        Class containing frequency information about a binary

        :param int computer_count: Number of endpoints this binary resides
        :param int process_count: Number of executions
        :param int all_process_count: Number of all process documents
        :param int module_frequency: process_count / all_process_count
        """
        pass

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

    @classmethod
    def _query_implementation(cls, cb):
        return WatchlistEnabledQuery(cls, cb)

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
        """
        Returns the Cb Response Web UI link associated with this Binary object
        """
        return '{0:s}/#binary/{1:s}'.format(self._cb.url, self.md5sum)

    @property
    def frequency(self):
        """
        Returns :class:`.FrequencyData` information about the binary.

        :example:

        >>> process_obj = c.select(Process).where('process_name:svch0st.exe').first()
        >>> binary_obj = process_obj.binary
        >>> print(binary_obj.frequency)
        FrequencyData(computer_count=1, process_count=5, all_process_count=4429, module_frequency=0.001128923007450892)
        """
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
        """
        Returns a file pointer to this binary

        :example:

        >>> process_obj = c.select(Process).where("process_name:svch0st.exe").first()
        >>> binary_obj = process_obj.binary
        >>> print(binary_obj.file.read(2))
        MZ
        """
        # TODO: I don't like reaching through to the session...
        with closing(self._cb.session.get("/api/v1/binary/{0:s}".format(self.md5sum), stream=True)) as r:
            z = StringIO(r.content)
            zf = ZipFile(z)
            fp = zf.open('filedata')
            return fp

    @property
    def observed_filenames(self):
        """
        Returns a list of all observed file names associated with this Binary
        """
        return self._attribute('observed_filename', [])

    @property
    def size(self):
        """
        Returns the size of the Binary
        """
        return long(self._attribute('orig_mod_len', 0))

    @property
    def copied_size(self):
        return long(self._attribute('copied_mod_len', 0))

    @property
    def endpoints(self):
        """
        Return a list of endpoints this binary resides
        """
        endpoint_list = self._attribute('endpoint', [])
        return [self._cb.select(Sensor, int(endpoint.split("|")[1]),
                                initial_data={"computer_name": endpoint.split("|")[0]})
                for endpoint in endpoint_list]

    @property
    def version_info(self):
        """
        Returns a :class:`.VersionInfo` object containing detailed information: File Descritpion, File Version,
        Product Name, Product Version, Company Name, Legal Copyright, and Original FileName
        """
        return Binary.VersionInfo._make([self._attribute('file_desc', ""), self._attribute('file_version', ""),
                                         self._attribute('product_name', ""), self._attribute('product_version', ""),
                                         self._attribute('company_name', ""), self._attribute('legal_copyright', ""),
                                         self._attribute('original_filename', "")])

    # Returns True if the binary contains a valid digital signature.
    # Returns False if the binary has no digital signature, if the signature is expired or otherwise
    # distrusted.
    @property
    def signed(self):
        """
        Returns True if the binary is signed.
        """
        if self._attribute('digsig_result', default="Unsigned") == 'Signed':
            return True
        else:
            return False

    @property
    def signing_data(self):
        """
        Returns :class:`.SigningData` object which contains: Digital Signature Result, Digital Signature publisher,
        Issuer, Subject, Signing Time, Program Name
        """
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
        """
        Returns the Digital Signature Publisher
        """
        return self._attribute('digsig_publisher', "")

    @property
    def digsig_issuer(self):
        """
        Returns the Digital Signature Issuer
        """
        return self._attribute('digsig_issuer', "")

    @property
    def digsig_subject(self):
        """
        Returns the Digital Signature subject
        """
        return self._attribute('digsig_subject', "")

    @property
    def digsig_sign_time(self):
        """
        Returns the Digital Signature signing time
        """
        return self._attribute('digsig_sign_time', "")

    @property
    def digsig_prog_name(self):
        """
        Returns the Digital Signature Program Name
        """
        return self._attribute('digsig_prog_name', "")

    @property
    def is_64bit(self):
        """
        Returns True if the Binary is an AMD64 or x64 (64-bit) Executable
        """
        return self._attribute('is_64bit', False)

    @property
    def is_executable_image(self):
        """
        Returns True if the Binary is executable
        """
        return self._attribute('is_executable_image', False)

    @property
    def icon(self):
        """
        Returns the raw icon of this Binary. This data is not encoded.
        """
        icon = ''
        try:
            icon = self._attribute('icon')
            if not icon:
                icon = ''
        except Exception:
            pass

        return base64.b64decode(icon)

    @property
    def banned(self):
        """
        Returns *BannedHash* object if this Binary's hash has been whitelisted (Banned), otherwise returns *False*
        """
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
        except Exception:
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
        new_childproc['terminated'] = True
        if parts[5] == 'true':
            new_childproc['terminated'] = False

        new_childproc['tamper_flag'] = False
        if len(parts) > 6 and parts[6] == 'true':
            new_childproc['tamper_flag'] = True

        new_childproc['suppressed'] = False

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
        if len(parts) > 8:
            if parts[8] == 'true':
                new_crossproc['is_target'] = True

        if new_crossproc['is_target']:
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
            except Exception:
                new_conn[ipfield] = netconn.get(ipfield, '0.0.0.0')

        for portfield in ('remote_port', 'local_port', 'proxy_port'):
            new_conn[portfield] = int(netconn.get(portfield, 0))

        new_conn['proto'] = protocols.get(int(netconn.get('proto', 0)), "Unknown")
        new_conn['domain'] = netconn.get('domain', '')

        return CbNetConnEvent(self.process_model, timestamp, seq, new_conn, version=2)


class ProcessV3Parser(ProcessV2Parser):
    def __init__(self, process_model):
        super(ProcessV3Parser, self).__init__(process_model)

    def parse_childproc(self, seq, childproc):
        new_childproc = {}
        new_childproc["procguid"] = childproc.get("processId", None)
        new_childproc["md5"] = childproc.get("md5", None)
        new_childproc["path"] = childproc.get("path", None)
        new_childproc["pid"] = childproc.get("pid", None)
        is_terminated = childproc.get("type", "start") == "end"
        new_childproc["terminated"] = is_terminated
        if is_terminated:
            timestamp = convert_event_time(childproc.get("end", None))
        else:
            timestamp = convert_event_time(childproc.get("start", None))

        new_childproc["tamper_flag"] = childproc.get("is_tampered", False)

        suppressed_flag = childproc.get("is_suppressed", False)
        proc_data = None
        if suppressed_flag:
            proc_data = {"cmdline": childproc.get("commandLine", None),
                         "username": childproc.get("userName", None)}

        return CbChildProcEvent(self.process_model, timestamp, seq, new_childproc, is_suppressed=suppressed_flag,
                                proc_data=proc_data)


class ProcessV4Parser(ProcessV3Parser):
    def __init__(self, process_model):
        super(ProcessV4Parser, self).__init__(process_model)

    def parse_netconn(self, seq, netconn):
        new_conn = {}
        timestamp = convert_event_time(netconn.get("timestamp", None))
        direction = netconn.get("direction", "true")

        if direction == 'true':
            new_conn['direction'] = 'Outbound'
        else:
            new_conn['direction'] = 'Inbound'

        for ipfield in ('remote_ip', 'local_ip', 'proxy_ip'):
            new_conn[ipfield] = netconn.get(ipfield, '0.0.0.0')

        for portfield in ('remote_port', 'local_port', 'proxy_port'):
            new_conn[portfield] = int(netconn.get(portfield, 0))

        new_conn['proto'] = protocols.get(int(netconn.get('proto', 0)), "Unknown")
        new_conn['domain'] = netconn.get('domain', '')

        return CbNetConnEvent(self.process_model, timestamp, seq, new_conn, version=2)


class Process(TaggedModel):
    urlobject = '/api/v1/process'
    default_sort = 'last_update desc'

    invalid_id = 'ffff-ffff-0000-000000000000'
    invalid_pid = -1
    invalid_name = '(unknown)'
    invalid_start = -1

    defaults = {                \
        'process_md5': '0' * 32 \
    }

    @classmethod
    def _query_implementation(cls, cb):
        return ProcessQuery(cls, cb)

    @classmethod
    def new_object(cls, cb, item, max_children=15):
        # 'id' did not exist in some process documents from a 5.2 -> 6.1 upgrade
        return cb.select(Process, item['id'] or item['unique_id'], long(item['segment_id']),
                         max_children, initial_data=item)

    @staticmethod
    def parse_guid(procguid, cb_server_version):
        try:
            # old 4.x process IDs are integers.
            return int(procguid), None
        except ValueError:
            # new 5.x process IDs are hex strings with optional segment IDs.
            if len(procguid) == 45:
                return procguid[:36], int(procguid[38:], 16)
            elif len(procguid) == 49 and cb_server_version >= LooseVersion('6.0.0'):
                return procguid[:36], int(procguid[38:], 16)
            else:
                return None, None

    def __init__(self, cb, procguid, segment=None, max_children=15, initial_data=None, force_init=False, suppressed_process=False):
        # Set version specific members
        self._default_segment = 1
        self._process_event_api = 'v1'
        self._process_summary_api = 'v1'
        self._event_parser = ProcessV1Parser(self)

        if cb.cb_server_version >= LooseVersion('6.0.0'):
            self._default_segment = 0
            self._process_event_api = 'v4'
            self._process_summary_api = 'v2'
            self._event_parser = ProcessV4Parser(self)
        elif cb.cb_server_version >= LooseVersion('5.2.0'):
            self._process_event_api = 'v3'
            self._event_parser = ProcessV3Parser(self)
        elif cb.cb_server_version >= LooseVersion('5.1.0'):
            self._process_event_api = 'v2'
            self._event_parser = ProcessV2Parser(self)

        # Set id and segment
        self.id, self.current_segment = Process.parse_guid(procguid, cb.cb_server_version)

        if not self.id:
            self.id = procguid

        if not self.current_segment:
            self.current_segment = segment or self._default_segment

        # NOTE: Sets self._full_init = False
        super(Process, self).__init__(cb, self.id)

        # Set object members
        self._events = {}
        self._segments = []
        self.__parent_info = {}
        self.__sibling_info = []
        self.__children_info = []
        self.valid_process = True
        self._events_loaded = False
        self.max_children = max_children
        self.suppressed_process = suppressed_process

        if len(self.id) != 36:
            self._full_init = True
            self.valid_process = False
            log.debug('Invalid process GUID: {}, declaring this process as invalid'.format(self.id))

        if self.suppressed_process:
            self._full_init = True
            log.debug('{0} is suppressed'.format(self.id))

        # Parse data
        if initial_data:
            self._parse({'process': copy.deepcopy(initial_data)})

        if force_init:
            self.refresh()

    @property
    def _parent_info(self):
        if not self._full_init:
            self.refresh()
        return self.__parent_info

    @property
    def _children_info(self):
        if not self._full_init:
            self.refresh()
        return self.__children_info

    @property
    def _sibling_info(self):
        if not self._full_init:
            self.refresh()
        return self.__sibling_info

    def _attribute(self, attrname, default=None):
        # workaround for Cb Response where parent_unique_id is returned as null
        # string as part of a query result. in this case we need to do a
        # full_init.
        #
        # Relaxing this a bit to allow for cases where the information is there
        if attrname in ['parent_unique_id',
                        'parent_name'] and not self._full_init:
            if attrname in self._info and self._info[attrname] is not None and self._info[attrname] != "":
                return self._info[attrname]
            else:
                self._retrieve_cb_info()

        return super(Process, self)._attribute(attrname, default=default)

    def _build_api_request_uri(self):
        return "/api/{0}/process/{1}/{2}?children={3}".format(self._process_summary_api, self.id, self._default_segment, self.max_children)

    def _retrieve_cb_info(self, query_parameters=None):
        if self.valid_process and not self.suppressed_process:
            super(Process, self)._retrieve_cb_info(query_parameters)

    def _parse_id_vars(self, proc_info, parent_info, sibling_info, children_info):
        INVALID_ID = self.__class__.invalid_id
        INVALID_PID = self.__class__.invalid_pid
        INVALID_START = self.__class__.invalid_start

        # Each information object is uniquely identified by the value of unique_id, which is
        # the concatenation of the process id and the segment id. The process id encodes the
        # value of start and process_pid, which we decode and use if possible and necessary.

        for info in chain([proc_info, parent_info], sibling_info, children_info):
            # Verify id and unique_id
            missing_or_invalid_id = INVALID_ID in info.get('id', INVALID_ID)
            missing_or_invalid_uid = INVALID_ID in info.get('unique_id', INVALID_ID)

            if missing_or_invalid_id and missing_or_invalid_uid:
                continue

            if missing_or_invalid_id:
                #old_id = info.get('id')
                info['id'] = info.get('unique_id')[:36]
                #logging.debug('Replacing missing or invalid id {} with {} while parsing {}'.format(old_id, info.get('id'), self.id))

            if missing_or_invalid_uid:
                #old_uid = info.get('unique_id')
                info['unique_id'] = '-'.join((info.get('id'), hex(self._default_segment)[2:].zfill(12)))
                #logging.debug('Replacing missing or invalid uid {} with {} while parsing {}'.format(old_uid, info.get('unique_id'), self.id))

            # Verify process_pid and start
            missing_or_invalid_pid = info.get('process_pid', INVALID_PID) == INVALID_PID
            missing_or_invalid_start = info.get('start', INVALID_START) == INVALID_START or info.get('start', INVALID_START) == None

            if missing_or_invalid_pid or missing_or_invalid_start:
                try:
                    _, process_pid, start = parse_process_guid(info.get('id'))
                except:
                    pass
                else:
                    #old_pid = info.get('process_pid')
                    #old_start = info.get('start')
                    info['process_pid'] = process_pid
                    info['start'] = convert_to_solr(start)
                    #logging.debug('Replacing missing or invalid pid {} with {} while parsing {}'.format(old_pid, info.get('process_pid'), self.id))
                    #logging.debug('Replacing missing or invalid start {} with {} while parsing {}'.format(old_start, info.get('start'), self.id))

    def _parse_proc_vars(self, proc_info, parent_info, sibling_info, children_info):
        INVALID_ID = self.__class__.invalid_id
        INVALID_PID = self.__class__.invalid_pid
        INVALID_NAME = self.__class__.invalid_name

        # Certain values in the process information object are replicated in other information
        # objects, e.g. the value of 'id' in the process information object equals the value of
        # 'parent_id' in all of the children information objects. However, the data is not always
        # consistent, resulting in incorrect results even though the correct data may be available
        # somewhere else. This parsing function first retrieves and deduplicates all known values of
        # different keys, deduplicates them, removes invalid ones and finally attempts to assert the
        # correct value and write it back to all of the relevant information objects.

        # Read subject process id, uid, pid and name from all possible objects
        process_ids = set([self._info.get('id', INVALID_ID), proc_info.get('id', INVALID_ID)] + \
                          [child.get('parent_id', INVALID_ID) for child in chain(self.__children_info, children_info)])
        process_uids = set([self._info.get('unique_id', INVALID_ID), proc_info.get('unique_id', INVALID_ID)] + \
                           [child.get('parent_unique_id', INVALID_ID) for child in chain(self.__children_info, children_info)])
        process_pids = set([self._info.get('process_pid', INVALID_PID), proc_info.get('process_pid', INVALID_PID)] + \
                           [child.get('parent_pid', INVALID_PID) for child in chain(self.__children_info, children_info)])
        process_names = set([self._info.get('process_name', INVALID_NAME), proc_info.get('process_name', INVALID_NAME)] + \
                            [child.get('parent_name', INVALID_NAME) for child in chain(self.__children_info, children_info)])

        # Remove invalid values
        process_ids = process_ids.difference(set([process_id for process_id in process_ids if INVALID_ID in process_id]))
        process_uids = process_uids.difference(set([process_uid for process_uid in process_uids if INVALID_ID in process_uids]))
        process_pids = process_pids.difference(set([INVALID_PID]))
        process_names = process_names.difference(set([INVALID_NAME]))

        # Set default values
        process_id = proc_info.get('id', INVALID_ID)
        process_uid = proc_info.get('unique_id', INVALID_ID)
        process_pid = proc_info.get('process_pid', INVALID_PID)
        process_name = proc_info.get('process_name', INVALID_NAME)

        # We must have at least one ID, but no more than one valid
        # process_id. Following is a table of acceptable combinations.
        #
        # OK | len(*_ids) | len(*_uids)
        # N  |      0     |      0
        # Y  |      0     |      1
        # Y  |      0     |      2..
        # Y  |      1     |      0
        # Y  |      1     |      1
        # Y  |      1     |      2..
        # N  |      2..   |      0
        # N  |      2..   |      1
        # N  |      2..   |      2..

        # Set valid values
        if len(process_ids) == 1:
            process_id = process_ids.pop()
        elif not process_ids and process_uids:
            process_id = process_uid.pop()[:36]
        #else:
        #    logging.debug('Missing, invalid or ambiguous process id(s) {} while parsing {}'.format(process_pids, self.id))

        process_uid = '-'.join((process_id, hex(self._default_segment)[2:].zfill(12)))

        if len(process_pids) == 1:
            process_pid = process_pids.pop()
        #else:
        #    logging.debug('Missing, invalid or ambiguous process pid(s) {} while parsing {}'.format(process_pids, self.id))

        if len(process_names) == 1:
            process_name = process_names.pop()
        #else:
        #    logging.debug('Missing, invalid or ambiguous process name(s) {} while parsing {}'.format(process_names, self.id))

        # Write values
        for info in [self._info, proc_info]:
            if not info:
                continue

            missing_or_invalid_id = INVALID_ID in info.get('id', INVALID_ID)
            missing_or_invalid_uid = INVALID_ID in info.get('unique_id', INVALID_ID)
            missing_or_invalid_pid = info.get('process_pid', INVALID_PID) == INVALID_PID
            missing_or_invalid_name = info.get('process_name', INVALID_NAME) == INVALID_NAME

            if missing_or_invalid_id:
                #old_id = info.get('id')
                info['id'] = process_id
                #logging.debug('Replacing missing or invalid process id {} with {} while parsing {}'.format(old_id, process_id, self.id))

            if missing_or_invalid_uid:
                #old_uid = info.get('unique_id')
                info['unique_id'] = process_uid
                #logging.debug('Replacing missing or invalid process uid {} with {} while parsing {}'.format(old_uid, process_uid, self.id))

            if missing_or_invalid_pid:
                #old_pid = info.get('process_pid')
                info['process_pid'] = process_pid
                #logging.debug('Replacing missing or invalid process pid {} with {} while parsing {}'.format(old_pid, process_pid, self.id))

            if missing_or_invalid_name:
                #old_name = info.get('process_name')
                info['process_name'] = process_name
                #logging.debug('Replacing missing or invalid process name {} with {} while parsing {}'.format(old_name, process_name, self.id))

        for info in chain(self.__children_info, children_info):
            if not info:
                continue

            missing_or_invalid_id = INVALID_ID in info.get('parent_id', INVALID_ID)
            missing_or_invalid_uid = INVALID_ID in info.get('parent_unique_id', INVALID_ID)
            missing_or_invalid_pid = info.get('parent_pid', INVALID_PID) == INVALID_PID
            missing_or_invalid_name = info.get('parent_name', INVALID_NAME) == INVALID_NAME

            if missing_or_invalid_id:
                #old_id = info.get('parent_id')
                info['parent_id'] = process_id
                #logging.debug('Replacing missing or invalid process id {} with {} while parsing {}'.format(old_id, process_id, self.id))

            if missing_or_invalid_uid:
                #old_uid = info.get('parent_unique_id')
                info['parent_unique_id'] = process_uid
                #logging.debug('Replacing missing or invalid process uid {} with {} while parsing {}'.format(old_uid, process_uid, self.id))

            if missing_or_invalid_pid:
                #old_pid = info.get('parent_pid')
                info['parent_pid'] = process_pid
                #logging.debug('Replacing missing or invalid process pid {} with {} while parsing {}'.format(old_pid, process_pid, self.id))

            if missing_or_invalid_name:
                #old_name = info.get('parent_name')
                info['parent_name'] = process_name
                #logging.debug('Replacing missing or invalid process name {} with {} while parsing {}'.format(old_name, process_name, self.id))

    def _parse_parent_vars(self, proc_info, parent_info, sibling_info, children_info):
        INVALID_ID = self.__class__.invalid_id
        INVALID_PID = self.__class__.invalid_pid
        INVALID_NAME = self.__class__.invalid_name

        # See _parse_proc_vars for rationalization and overview. This parsing function does basically
        # the same thing, except for parent_* values in the process information object.

        parent_ids = set([info.get('parent_id', INVALID_ID) for info in \
                          chain([self._info, proc_info], self.__sibling_info, sibling_info)])
        parent_uids = set([info.get('parent_unique_id', INVALID_ID) for info in \
                           chain([self._info, proc_info], self.__sibling_info, sibling_info)])
        parent_pids = set([info.get('parent_pid', INVALID_PID) for info in \
                           chain([self._info, proc_info], self.__sibling_info, sibling_info)])
        parent_names = set([info.get('parent_name', INVALID_NAME) for info in \
                            chain([self._info, proc_info], self.__sibling_info, sibling_info)])

        parent_ids = parent_ids.difference(set([parent_id for parent_id in parent_ids if INVALID_ID in parent_id]))
        parent_uids = parent_uids.difference(set([parent_uid for parent_uid in parent_uids if INVALID_ID in parent_uid]))
        parent_pids = parent_pids.difference(set([INVALID_PID]))
        parent_names = parent_names.difference(set([INVALID_NAME]))

        parent_id = proc_info.get('parent_id', INVALID_ID)
        parent_uid = proc_info.get('parent_unique_id', INVALID_ID)
        parent_pid = proc_info.get('parent_pid', INVALID_PID)
        parent_name = proc_info.get('parent_name', INVALID_NAME)

        if len(parent_ids) == 1:
            parent_id = parent_ids.pop()
        elif not parent_ids and parent_uids:
            parent_id = parent_uids.pop()[:36]
        #else:
        #    logging.debug('Missing, invalid or ambiguous parent id(s) {} while parsing {}'.format(parent_ids, self.id))

        parent_uid = '-'.join((parent_id, hex(self._default_segment)[2:].zfill(12)))

        if len(parent_pids) == 1:
            parent_pid = parent_pids.pop()
        #else:
        #    logging.debug('Missing, invalid or ambiguous parent pid(s) {} while parsing {}'.format(parent_pids, self.id))

        if len(parent_names) == 1:
            parent_name = parent_names.pop()
        #else:
        #    logging.debug('Missing, invalid or ambiguous parent name(s) {} while parsing {}'.format(parent_names, self.id))

        for info in chain([self._info, proc_info], self.__sibling_info, sibling_info):
            if not info:
                continue

            missing_or_invalid_id = INVALID_ID in info.get('parent_id', INVALID_ID)
            missing_or_invalid_uid = INVALID_ID in info.get('parent_unique_id', INVALID_ID)
            missing_or_invalid_pid = info.get('parent_pid', INVALID_PID) == INVALID_PID
            missing_or_invalid_name = info.get('parent_name', INVALID_NAME) == INVALID_NAME

            if missing_or_invalid_id:
                #old_id = info.get('parent_id')
                info['parent_id'] = parent_id
                #logging.debug('Replacing missing or invalid parent id {} with {} while parsing {}'.format(old_id, parent_id, self.id))

            if missing_or_invalid_uid:
                #old_uid = info.get('parent_unique_id')
                info['parent_unique_id'] = parent_uid
                #logging.debug('Replacing missing or invalid parent uid {} with {} while parsing {}'.format(old_uid, parent_uid, self.id))

            if missing_or_invalid_pid:
                #old_pid = info.get('parent_pid')
                info['parent_pid'] = parent_pid
                #logging.debug('Replacing missing or invalid parent pid {} with {} while parsing {}'.format(old_pid, parent_pid, self.id))

            if missing_or_invalid_name:
                #old_name = info.get('parent_name')
                info['parent_name'] = parent_name
                #logging.debug('Replacing missing or invalid parent name {} with {} while parsing {}'.format(old_name, parent_name, self.id))

    def _parse(self, obj):
        # Get information objects
        proc_info = obj.get("process", obj)
        parent_info = obj.get("parent", dict())
        sibling_info = obj.get("siblings", list())
        children_info = obj.get("children", list())

        # Determine id, uid, pid, start for all information objects
        self._parse_id_vars(proc_info, parent_info, sibling_info, children_info)

        # Determine process_id, process_uid, process_pid and process_name for process, sibling and children information objects
        self._parse_proc_vars(proc_info, parent_info, sibling_info, children_info)

        # Determine parent_id, parent_unique_id, parent_pid, parent_name for process and sibling information objects
        self._parse_parent_vars(proc_info, parent_info, sibling_info, children_info)

        # Avoid updating keys that are already populated and have no defaults with invalid values
        if self._info.get('cmdline') and not proc_info.get('cmdline'):
            proc_info.pop('cmdline', None)

        if self._info.get('username') and not proc_info.get('username'):
            proc_info.pop('username', None)

        if self._info.get('start') and proc_info.get('start', int()) == -1:
            proc_info.pop('start', None)

        # Avoid updating keys that have defaults with invalid values
        if len(proc_info.get('process_md5', str())) != 32:
            proc_info.pop('process_md5', None)

        # Update and extend
        def update(old, new):
            info_dict = {info['id']:info for info in old}

            for info in new:
                key = info['id']

                if key not in info_dict:
                    info_dict[key] = info
                else:
                    info_dict[key].update(info)

            return list(info_dict.values())

        self._info.update(proc_info)
        self.__parent_info.update(parent_info)
        self.__sibling_info = update(self.__sibling_info, sibling_info)
        self.__children_info = update(self.__children_info, children_info)

        # Set missing defaults
        defaults = self.__class__.defaults

        for kw in defaults:
            if kw not in self._info:
                self._info[kw] = defaults[kw]

        # 7/31/2018: remove parent_md5 from the _info array, as it's never set.
        #  instead add an accessor to transparently request the process_md5 from the parent.
        if self._info.get('parent_md5'):
            del self._info['parent_md5']

    def walk_parents(self, callback, max_depth=0, depth=0):
        """
        Walk up the execution chain while calling the specified callback function at each depth.

        :Example:

        >>> def proc_callback(parent_proc, depth):
        ...    print(parent_proc.cmdline, depth)
        >>>
        >>> process = c.select(Process).where('process_name:ipconfig.exe')[0]
        >>> process.walk_parents(proc_callback)
        (u'cmd.exe /c ipconfig.exe', 0)
        (u'c:\\windows\\carbonblack\\cb.exe', 1)
        (u'C:\\Windows\\system32\\services.exe', 2)
        (u'wininit.exe', 3)
        (u'\\SystemRoot\\System32\\smss.exe 00000000 00000040 ', 4)
        (u'\\SystemRoot\\System32\\smss.exe', 5)
        (u'', 6)

        :param func callback: Callback function used for execution at each depth.
            This function is executed with the parent process object and depth as parameters.
        :param int max_depth: Max number of iterations up the execution chain
        :param int depth: Number of iterations up the execution chain.
        :return: None
        """
        if max_depth and depth > max_depth:
            return

        try:
            parent_proc = self.parent
            if parent_proc and parent_proc.get("process_pid", -1) != -1:
                callback(parent_proc, depth=depth)
            else:
                return
        except ObjectNotFoundError:
            return
        else:
            parent_proc.walk_parents(callback, max_depth=max_depth, depth=depth+1)

    def walk_children(self, callback, max_depth=0, depth=0):
        """
        Walk down the execution chain while calling the specified callback function at each depth.

        :example:

        >>> def proc_callback(parent_proc, depth):
        ...     print(parent_proc.cmdline, depth)
        >>>
        >>> process = c.select(Process).where('process_name:svch0st.exe')[0]
        >>> process.walk_children(proc_callback, depth=2)
        (u'cmd.exe \\c ipconfig', 2)
        (u'cmd.exe \\\\c ipconfig', 2)
        (u'cmd.exe /c ipconfig', 2)
        (u'ipconfig', 3)
        (u'cmd.exe /c ipconfig.exe /all', 2)
        (u'cmd.exe \\c ipconfig', 2)
        (u'cmd.exe \\\\c ipconfig', 2)
        (u'cmd.exe /c ipconfig', 2)
        (u'ipconfig', 3)
        (u'cmd.exe /c ipconfig.exe /all', 2)

        :param func callback: Callback function used for execution at each depth.
            This function is executed with the parent process object and depth as parameters.
        :param int max_depth: Max number of iterations down the execution chain.
        :param int depth: Number of iterations down the execution chain
        :return: None
        """
        if max_depth and depth > max_depth:
            return

        for cpevent in self.children:
            if not cpevent.terminated:
                try:
                    proc = cpevent.process
                    callback(proc, depth=depth)
                except ObjectNotFoundError:
                    continue
                else:
                    proc.walk_children(callback, max_depth=max_depth, depth=depth+1)

    @property
    def parent_md5(self):
        """
        Workaround since parent_md5 silently disappeared in ~Cb Response 6.x
        """
        return self.parent.process_md5

    @property
    def start(self):
        """
        Returns the start time of the process
        """
        if self.get("start") is not None:
            return convert_from_solr(self._attribute('start', -1))
        else:
            return None

    @property
    def end(self):
        """
        Returns the end time of the process (based on the last event received). If the process has not yet exited,
        "end" will return None.

        :return: datetime object of the last event received for the process, if it has terminated. Otherwise, None.
        """
        if self._info.get("end") is not None:
            return convert_from_solr(self._info.get('end', -1))

        if self.get("terminated", False) and self.get("last_update") is not None:
            return convert_from_solr(self._attribute('last_update', -1))

    def require_events(self, segment=0, min_last_update=None, max_last_update=None):
        event_types = {
                'filemod_count': 'filemod_complete',
                'regmod_count': 'regmod_complete',
                'modload_count': 'modload_complete',
                'netconn_count': 'netconn_complete',
                'crossproc_count': 'crossproc_complete',
                'childproc_count': 'childproc_complete'
                }

        if self._events_loaded:
            return
        if not self.valid_process:
            return
        if self.suppressed_process:
            return

        if segment not in self._events:
            # Prepare
            start = 0
            count = 10000 # Backend default
            base_url = '/api/{0}/process/{1}/{2}/event?'.format(self._process_event_api, self.id, segment)

            if min_last_update:
                base_url += 'cb.min_last_update={0:%Y-%m-%dT%H:%M:%SZ}&'.format(min_last_update)
            if max_last_update:
                base_url += 'cb.max_last_update={0:%Y-%m-%dT%H:%M:%SZ}&'.format(max_last_update)

            events = {event_complete:[] for event_complete in event_types.values()}

            # Fetch and store events
            while True:
                url = base_url
                url += 'cb.event_start={0}&'.format(start)
                url += 'cb.event_count={0}&'.format(count)

                res = self._cb.get_object(url)
                proc = res.get('process', {})

                num_events = 0
                for event_complete in event_types.values():
                    proc_event_complete = proc.get(event_complete, [])
                    num_events += len(proc_event_complete)
                    events[event_complete].extend(proc_event_complete)

                # Note that there might be more events even though we got less than we
                # asked for. Thus, break out of loop once we don't recieve any more events.
                if not num_events:
                    break

                start += count

            self._events[segment] = events

            # Update process info
            for event_count, event_complete in event_types.items():
                if event_count in proc:
                    del proc[event_count]

                if event_complete in proc:
                    del proc[event_complete]

            self._parse(res)
            #self._full_init = True

            # Append events to process info
            for event_count, event_complete in event_types.items():
                self._info[event_complete] = self._info.get(event_complete, [])
                self._info[event_count] = self._info.get(event_count, 0)

                self._info[event_complete].extend(self._events[segment][event_complete])
                self._info[event_count] += len(self._info[event_complete])

        # All events loaded
        self._events_loaded = segment == 0

    def refresh(self):
        # when refreshing a process, also zero out all the events
        self._events = {}
        self._events_loaded = False
        self._segments = []
        super(Process, self).refresh()

    @property
    def segment(self):
        log.debug("The .segment attribute will be deprecated in future versions of the cbapi Python module.")
        return self.current_segment

    @property
    def modloads(self):
        """
        Generator that returns `:py:class:CbModLoadEvent` associated with this process
        """
        self.require_events(segment=self.current_segment)

        i = 0
        for segment in self._events:
            for raw_modload in self._events[segment].get('modload_complete', []):
                yield self._event_parser.parse_modload(i, raw_modload)
                i += 1

    @property
    def unsigned_modloads(self):
        """
        Returns all unsigned module loads.  This is useful to filter out all Microsoft signed DLLs
        """
        return [m for m in self.modloads if not m.is_signed]

    @property
    def filemods(self):
        """
        Generator that returns :py:class:`CbFileModEvent` objects associated with this process
        """
        self.require_events(segment=self.current_segment)

        i = 0
        for segment in self._events:
            for raw_filemod in self._events[segment].get('filemod_complete', []):
                yield self._event_parser.parse_filemod(i, raw_filemod)
                i += 1

    @property
    def netconns(self):
        """
        Generator that returns :py:class:`CbNetConnEvent` objects associated with this process
        """
        self.require_events(segment=self.current_segment)

        i = 0
        for segment in self._events:
            for raw_netconn in self._events[segment].get('netconn_complete', []):
                yield self._event_parser.parse_netconn(i, raw_netconn)
                i += 1

    @property
    def regmods(self):
        """
        Generator that returns :py:class:`CbRegModEvent` objects associated with this process
        """
        self.require_events(segment=self.current_segment)

        i = 0
        for segment in self._events:
            for raw_regmod in self._events[segment].get('regmod_complete', []):
                yield self._event_parser.parse_regmod(i, raw_regmod)
                i += 1

    @property
    def crossprocs(self):
        """
        Generator that returns :py:class:`CbCrossProcEvent` objects associated with this process
        """
        self.require_events(segment=self.current_segment)

        i = 0
        for segment in self._events:
            for raw_crossproc in self._events[segment].get('crossproc_complete', []):
                yield self._event_parser.parse_crossproc(i, raw_crossproc)
                i += 1

    @property
    def childprocs(self):
        """
        Generator that returns :py:class:`CbChildProcEvent` objects associated with this process
        """
        self.require_events(segment=self.current_segment)

        i = 0
        for segment in self._events:
            for raw_childproc in self._events[segment].get('childproc_complete', []):
                yield self._event_parser.parse_childproc(i, raw_childproc)
                i += 1

    @property
    def parents(self):
        current_process = self
        while True:
                try :
                    parent = current_process.parent
                    if not(parent) or parent.get('process_pid',-1) == -1:
                        break
                    yield parent
                    current_process = parent
                except ObjectNotFoundError:
                    return
        return

    @property
    def children(self):
        """
        Generator that returns :py:class:`Process` objects of the children of this process
        """

        # Generate a list of children as the union of the children in the process summary and childprocs, as either
        # one of the two might be incomplete.

        def parse_childinfo(childinfo):
            procguid = childinfo['unique_id']
            suppressed_process = childinfo.get('is_suppressed', False)

            childinfo['parent_id'] = self.id
            childinfo['parent_unique_id'] = self._model_unique_id
            childinfo['parent_md5'] = self.process_md5
            childinfo['parent_pid'] = self.process_pid
            childinfo['parent_name'] = self.process_name
            childinfo['group'] = self._info['group']
            childinfo['os_type'] = self._info['os_type']
            childinfo['hostname'] = self._info['hostname']
            childinfo['interface_ip'] = self._info['interface_ip']

            if not childinfo.get('id'):
                childinfo['id'] = '-'.join(procguid.split('-')[:5])

            if not childinfo.get('start'):
                proc_createtime = parse_process_guid(procguid)[2]
                childinfo['start'] = convert_to_solr(proc_createtime)

            if not childinfo.get('last_update') and childinfo.get('lastUpdate'):
                childinfo['last_update'] = childinfo['lastUpdate']
                del childinfo['lastUpdate']

            return self._cb.select(Process, procguid, initial_data=childinfo, suppressed_process=suppressed_process)

        childprocs = (childproc.process for childproc in self.childprocs)
        childinfos = (parse_childinfo(childinfo) for childinfo in self._children_info)

        ids = set()
        for child in chain(childprocs, childinfos):
            if child.id in ids:
                continue

            ids.add(child.id)
            yield child

    @property
    def all_events_segment(self):
        """
        Returns a list of all events associated with this process segment, sorted by timestamp

        :return: list of CbEvent objects
        """
        segment_events = list(self.modloads) + list(self.netconns) + list(self.filemods) + \
            list(self.children) + list(self.regmods) + list(self.crossprocs)
        segment_events.sort()
        return segment_events

    def get_segments(self):
        if not self._segments:
            if self._cb.cb_server_version < LooseVersion('6.0.0'):
                log.debug("using process_id search for cb response server < 6.0")
                segment_query = Query(Process, self._cb, query="process_id:{0}".format(self.id)).sort("")
                proclist = sorted([res["segment_id"] for res in segment_query._search()])
            else:
                log.debug("using segment API route for cb response server >= 6.0")
                res = self._cb.get_object("/api/v1/process/{0}/segment".format(self.id))\
                    .get("process", {}).get("segments", {})
                proclist = [Process.parse_guid(x["unique_id"], self._cb.cb_server_version)[1] for x in res]

            self._segments = proclist

        return self._segments

    @property
    def all_events(self):
        """
        Returns a list of all events associated with this process across all segments, sorted by timestamp

        :return: list of CbEvent objects
        """

        all_events = []

        # first let's find the list of segments
        segmentlist = self.get_segments()
        for segment in segmentlist:
            self.current_segment = segment
            all_events += self.all_events_segment

        return all_events

    @property
    def depth(self):
        """
        Returns the depth of this process from the "root" system process

        :return: integer representing the depth of the process (0 is the root system process). To prevent infinite
         recursion, a maximum depth of 500 processes is enforced.
        """

        depth = 0
        MAX_DEPTH = 500

        proc = self
        visited = []

        while depth < MAX_DEPTH:
            try:
                proc = proc.parent
            except ObjectNotFoundError:
                break
            else:
                current_proc_id = proc.id
                depth += 1

            if current_proc_id in visited:
                raise ApiError("Process cycle detected at depth {0}".format(depth))
            else:
                visited.append(current_proc_id)

        return depth

    @property
    def threat_intel_hits(self):
        try:
            hits = self._cb.get_object("/api/v1/process/{0}/{1}/threat_intel_hits".format(self.id,
                                                                                          self.current_segment))
            return hits
        except ServerError:
            raise ApiError("Sharing IOCs not set up in Cb server. See {}/#/share for more information."
                           .format(self._cb.credentials.url))

    @property
    def tamper_events(self):
        return [e for e in self.all_events if e.tamper_event]

    def find_file_writes(self, filename):
        """
        Returns a list of file writes with the specified filename

        :param str filename: filename to match on file writes
        :return: Returns a list of file writes with the specified filename
        :rtype: list
        """
        return [filemod for filemod in self.filemods if filemod.path == filename]

    @property
    def binary(self):
        """
        Joins this attribute with the :class:`.Binary` object associated with this Process object

        :example:

        >>> process_obj = c.select(Process).where('process_name:svch0st.exe')[0]
        >>> binary_obj = process_obj.binary
        >>> print(binary_obj.signed)
        False

        """
        binary_md5 = self.get('process_md5')
        if binary_md5:
            return self._cb.select(Binary, binary_md5)
        else:
            return None

    @property
    def comms_ip(self):
        """
        Returns ascii representation of the ip address used to communicate with the Cb Response Server
        """
        try:
            ip_address = socket.inet_ntoa(struct.pack('>i', self._attribute('comms_ip', 0)))
        except Exception:
            ip_address = self._attribute('comms_ip', 0)

        return ip_address

    @property
    def interface_ip(self):
        """
        Returns ascii representation of the ip address of the interface used to communicate with the Cb Response server.
        If using NAT, this will be the "internal" IP address of the sensor.
        """
        try:
            ip_address = socket.inet_ntoa(struct.pack('>i', self._attribute('interface_ip', 0)))
        except Exception:
            ip_address = self._attribute('interface_ip', 0)

        return ip_address

    @property
    def process_md5(self):
        # Some processes don't have an MD5 associated with them. Try and use the first modload as the MD5
        # otherwise, return None. (tested with Cb Response server 5.2.0.161004.1206)
        try:
            return self._attribute("process_md5", "") or next(self.modloads).md5
        except StopIteration:
            return None

    @property
    def path(self):
        # Some processes don't have a path associated with them. Try and use the first modload as the file path
        # otherwise, return None. (tested with Cb Response server 5.2.0.161004.1206)
        try:
            return self._attribute("path", "") or next(self.modloads).path
        except StopIteration:
            return None

    @property
    def parent(self):
        """
        Returns the parent Process object if one exists
        """
        parent_unique_id = self.get_correct_parent_unique_id()
        if not parent_unique_id:
            return None

        if isinstance(parent_unique_id, six.string_types):
            # strip off the segment number since we're just looking for the parent process, not a specific event
            parent_unique_id = "-".join(parent_unique_id.split("-")[:5])

        if self._full_init:
            return self._cb.select(self.__class__, parent_unique_id, initial_data=self._parent_info)
        else:
            return self._cb.select(self.__class__, parent_unique_id)

    @property
    def cmdline(self):
        """
        :return: Returns the command line of the process
        :rtype: string
        """
        cmdline = self.get('cmdline')
        if not cmdline:
            return self.path
        else:
            return cmdline

    @property
    def sensor(self):
        """
        Joins this attribute with the :class:`.Sensor` object associated with this Process object

        :example:

        >>> process_obj = c.select(Process).where('process_name:svch0st.exe')[0]
        >>> sensor_obj = process.sensor
        >>> print(sensor_obj.computer_dns_name)
        hyperv-win7-x86
        """
        sensor_id = self.get("sensor_id")
        if sensor_id:
            return self._cb.select(Sensor, int(sensor_id))
        else:
            return None

    @property
    def webui_link(self):
        """
        Returns the Cb Response Web UI link associated with this process
        """
        if not self.suppressed_process:
            return '%s/#analyze/%s/%s' % (self._cb.url, self.id, self.current_segment)
        else:
            return None

    def get_correct_parent_unique_id(self):
        # this is required for the new 4.2 style GUIDs...
        parent_unique_id = self.get('parent_unique_id', None)
        if not parent_unique_id:
            return self.get('parent_id', None)

        (sensor_id, proc_pid, proc_createtime) = parse_42_guid(parent_unique_id)
        if sensor_id != self.sensor.id:
            return self.get('parent_id', None)
        else:
            return parent_unique_id

    @property
    def last_update(self):
        """
        Returns a pretty version of when this process last updated
        """
        return convert_from_solr(self.get('last_update', -1))


    @property
    def min_last_update(self):
        """
        Returns a pretty version of the earliest event in this process segment
        """
        return convert_from_solr(self.get('min_last_update', -1))

    @property
    def max_last_update(self):
        """
        Returns a pretty version of the latest event in this process segment
        """
        return convert_from_solr(self.get('max_last_update', -1))

    @property
    def last_server_update(self):
        """
        Returns a pretty version of when this process last updated
        """
        return convert_from_solr(self.get('last_server_update', -1))

    @property
    def min_last_server_update(self):
        """
        Returns a pretty version of the earliest event in this process segment
        """
        return convert_from_solr(self.get('min_last_server_update', -1))

    @property
    def max_last_server_update(self):
        """
        Returns a pretty version of the latest event in this process segment
        """
        return convert_from_solr(self.get('max_last_server_update', -1))

    @property
    def username(self):
        """
        Returns the username of the owner of this process
        """
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
        super(CbModLoadEvent, self).__init__(parent_process, timestamp, sequence, event_data)
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
        super(CbFileModEvent, self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb File Modification event'
        self.stat_titles.extend(['type', 'path', 'filetype', 'md5'])


class CbRegModEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data):
        super(CbRegModEvent, self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Registry Modification event'
        self.stat_titles.extend(['type', 'path'])


class CbNetConnEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data, version=1):
        super(CbNetConnEvent, self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Network Connection event'
        self.stat_titles.extend(['domain', 'remote_ip', 'remote_port', 'proto', 'direction'])
        if version == 2:
            self.stat_titles.extend(['local_ip', 'local_port', 'proxy_ip', 'proxy_port'])


class CbChildProcEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data, is_suppressed=False, proc_data=None):
        super(CbChildProcEvent, self).__init__(parent_process, timestamp, sequence, event_data)
        self.event_type = u'Cb Child Process event'
        self.stat_titles.extend(['procguid', 'pid', 'path', 'md5'])
        self.is_suppressed = is_suppressed
        if proc_data:
            self.proc_data = copy.deepcopy(proc_data)
        else:
            self.proc_data = {}

    @property
    def process(self):
        self.proc_data["path"] = self.path
        self.proc_data["process_md5"] = self.md5
        self.proc_data["process_pid"] = self.pid
        self.proc_data["id"] = "-".join(self.procguid.split("-")[:5])
        self.proc_data["unique_id"] = self.procguid
        self.proc_data["terminated"] = self.terminated

        self.proc_data["parent_id"] = self.parent.id
        self.proc_data["parent_unique_id"] = self.parent._model_unique_id
        self.proc_data["parent_md5"] = self.parent.process_md5
        self.proc_data["parent_pid"] = self.parent.process_pid
        self.proc_data["parent_name"] = self.parent.process_name
        self.proc_data["group"] = self.parent._info["group"]
        self.proc_data["os_type"] = self.parent._info["os_type"]
        self.proc_data["hostname"] = self.parent._info["hostname"]
        self.proc_data["interface_ip"] = self.parent._info["interface_ip"]

        sensor_id, _, proc_createtime = parse_process_guid(self.procguid)
        self.proc_data["start"] = convert_to_solr(proc_createtime)
        self.proc_data["sensor_id"] = sensor_id

        self.proc_data["last_update"] = self.proc_data["start"]
        if self.terminated:
            self.proc_data["last_update"] = convert_to_solr(self.timestamp)

        return self.parent._cb.select(Process, self.procguid, initial_data=self.proc_data,
                                      suppressed_process=self.is_suppressed)


class CbCrossProcEvent(CbEvent):
    def __init__(self, parent_process, timestamp, sequence, event_data):
        super(CbCrossProcEvent, self).__init__(parent_process, timestamp, sequence, event_data)
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
