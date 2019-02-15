from __future__ import absolute_import
from cbapi.errors import ApiError, InvalidObjectError
from cbapi.models import NewBaseModel, CreatableModelMixin, MutableBaseModel
import logging
from cbapi.psc.threathunter.query import Query, AsyncProcessQuery, TreeQuery, FeedQuery, ReportQuery, WatchlistQuery
import validators

log = logging.getLogger(__name__)


class UnrefreshableModelMixin(NewBaseModel):
    """Represents a model that can't be refreshed, i.e. for which ``reset()``
    is not a valid operation.
    """
    def refresh(self):
        raise ApiError("refresh() called on an unrefreshable model")


class FeedModel(UnrefreshableModelMixin, CreatableModelMixin, MutableBaseModel):
    """A common base class for models used by the Feed and Watchlist APIs.
    """
    pass


class Process(UnrefreshableModelMixin):
    """Represents a process retrieved by one of the CbTH endpoints.
    """
    default_sort = 'last_update desc'
    primary_key = "process_guid"
    validation_url = "/pscr/query/v1/validate"

    @classmethod
    def _query_implementation(cls, cb):
        # This will emulate a synchronous process query, for now.
        return AsyncProcessQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Process, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                      force_init=force_init, full_doc=full_doc)

    def events(self, **kwargs):
        """Returns a query for events associated with this process's process GUID.

        :param kwargs: Arguments to filter the event query with.
        :return: Returns a Query object with the appropriate search parameters for events
        :rtype: :py:class:`cbapi.psc.threathunter.query.Query`

        Example::

        >>> [print(event) for event in process.events()]
        >>> [print(event) for event in process.events(event_type="modload")]
        """
        query = self._cb.select(Event).where(process_guid=self.process_guid)

        if kwargs:
            query = query.and_(**kwargs)

        return query

    def tree(self):
        """Returns a :py:class:`Tree` of children (and possibly siblings) associated with this process.

        :return: Returns a :py:class:`Tree` object
        :rtype: :py:class:`Tree`

        Example:

        >>> tree = process.tree()
        """
        data = self._cb.select(Tree).where(process_guid=self.process_guid).all()
        return Tree(self._cb, initial_data=data)

    @property
    def parents(self):
        """Returns a query for parent processes associated with this process.

        :return: Returns a Query object with the appropriate search parameters for parent processes, or None if the process has no recorded parent
        :rtype: :py:class:`cbapi.psc.threathunter.query.AsyncProcessQuery` or None
        """
        if "parent_guid" in self._info:
            return self._cb.select(Process).where(process_guid=self.parent_guid)
        else:
            return []

    @property
    def children(self):
        """Returns a list of child processes for this process.

        :return: Returns a list of process objects
        :rtype: list of :py:class:`Process`
        """
        return self.tree().children

    @property
    def siblings(self):
        # NOTE(ww): This shold be provided by the /tree endpoint eventually,
        # but currently isn't.
        raise ApiError("siblings() unimplemented")

    @property
    def process_md5(self):
        """Returns a string representation of the MD5 hash for this process.

        :return: A string representation of the process's MD5.
        :rtype: str
        """
        # NOTE: We have to check _info instead of poking the attribute directly
        # to avoid the missing attrbute login in NewBaseModel.
        if "process_hash" in self._info:
            return next((hsh for hsh in self.process_hash if len(hsh) == 32), None)
        else:
            return None

    @property
    def process_sha256(self):
        """Returns a string representation of the SHA256 hash for this process.

        :return: A string representation of the process's SHA256.
        :rtype: str
        """
        if "process_hash" in self._info:
            return next((hsh for hsh in self.process_hash if len(hsh) == 64), None)
        else:
            return None

    @property
    def process_pids(self):
        """Returns a list of PIDs associated with this process.

        :return: A list of PIDs
        :rtype: list of ints
        """
        # NOTE(ww): This exists because the API returns the list as "process_pid",
        # which is misleading. We just give a slightly clearer name.
        return self.process_pid

    def __repr__(self):
        return "<%s.%s: process id %s document id %s> @ %s" % (self.__class__.__module__, self.__class__.__name__,
                                                               self.process_guid, self.document_guid,
                                                               self._cb.session.server)


class Event(UnrefreshableModelMixin):
    """Events can be queried for via ``CbThreatHunterAPI.select``
    or though an already selected process with ``Process.events()``.
    """
    urlobject = '/pscr/query/v1/events'
    validation_url = '/pscr/query/v1/events/validate'
    default_sort = 'last_update desc'
    primary_key = "process_guid"

    @classmethod
    def _query_implementation(cls, cb):
        return Query(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Event, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                    force_init=force_init, full_doc=full_doc)


class Tree(UnrefreshableModelMixin):
    """The preferred interface for interacting with Tree models
    is ``Process.tree()``.
    """
    urlobject = '/pscr/query/v2/tree'
    primary_key = 'process_guid'

    @classmethod
    def _query_implementation(cls, cb):
        return TreeQuery(cls, cb)

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Tree, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                   force_init=force_init, full_doc=full_doc)

    @property
    def children(self):
        """Returns all of the children of the process that this tree is centered around.

        :return: A list of :py:class:`Process` instances
        :rtype: list of :py:class:`Process`
        """
        return [Process(self._cb, initial_data=child) for child in self.nodes["children"]]


class Feed(FeedModel):
    """Represents a ThreatHunter feed's metadata.
    """
    urlobject = "/threathunter/feedmgr/v1/feed"
    urlobject_single = "/threathunter/feedmgr/v1/feed/{}"
    primary_key = "id"
    swagger_meta_file = "psc/threathunter/models/feed.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return FeedQuery(cls, cb)

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        item = {}
        reports = []

        if initial_data:
            # NOTE(ww): Some endpoints give us the full Feed, others give us just the FeedInfo.
            if "feedinfo" in initial_data:
                item = initial_data["feedinfo"]
                reports = initial_data.get("reports", [])
            else:
                item = initial_data
        elif model_unique_id:
            # TODO(ww): It's probably bad practice to make a request here.
            # Maybe abstract this into a separate method?
            resp = cb.get_object(self.urlobject_single.format(model_unique_id))
            item = resp.get("feedinfo", {})
            reports = resp.get("reports", [])

        feed_id = item.get("id")

        super(Feed, self).__init__(cb, model_unique_id=feed_id, initial_data=item,
                                   force_init=force_init, full_doc=full_doc)

        self._reports = [Report(cb, initial_data=report, feed_id=feed_id) for report in reports]

    def save(self):
        self.validate()

        body = {
            'feedinfo': self._info,
            'reports': [report._info for report in self._reports],
        }

        new_info = self._cb.post_object("/threathunter/feedmgr/v1/feed", body).json()
        self._info.update(new_info)
        return self

    def validate(self):
        super(Feed, self).validate()

        if self.access not in ["public", "private"]:
            raise InvalidObjectError("access should be public or private")

        if not validators.url(self.provider_url):
            raise InvalidObjectError("provider_url should be a valid URL")

        for report in self._reports:
            report.validate()

        # TODO(ww): Any other field-specific validation required?

    def delete(self):
        if not self.id:
            raise InvalidObjectError("missing feed ID")

        self._cb.delete_object("/threathunter/feedmgr/v1/feed/{}".format(self.id))

    def update(self, **kwargs):
        if not self.id:
            raise InvalidObjectError("missing feed ID")

        for key, value in kwargs.items():
            if key not in self._info:
                raise ApiError("can't update nonexistent field {}".format(key))

        new_info = self._cb.put_object("/threathunter/feedmgr/v1/feed/{}/feedinfo".format(self.id), kwargs).json()
        self._info.update(new_info)
        return self

    @property
    def reports(self):
        # TODO(ww): Short circuit on self._reports?
        return self._cb.select(Report).where(feed_id=self.id)

    def replace(self, reports, append=False):
        if not self.id:
            raise ApiError("missing feed ID")

        rep_dicts = [report._info for report in reports]

        if append:
            rep_dicts += [report._info for report in self._reports]

        body = {"reports": rep_dicts}

        self._cb.post_object("/threathunter/feedmgr/v1/{}/report".format(self.id), body)


class Report(FeedModel):
    """Represents reports retrieved from a ThreatHunter feed.
    """
    urlobject = "/threathunter/feedmgr/v1/feed/{}/report"
    primary_key = "id"
    swagger_meta_file = "psc/threathunter/models/report.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return ReportQuery(cls, cb)

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True, feed_id=None):
        super(Report, self).__init__(cb, model_unique_id=initial_data.get("id"), initial_data=initial_data,
                                     force_init=force_init, full_doc=full_doc)

        # NOTE(ww): Warn instead of failing, since not all report operations
        # require a feed ID.
        if not feed_id:
            log.warning("Report created without feed ID")

        self._feed_id = feed_id

        if self.iocs:
            self._iocs = IOCs(cb, initial_data=self.iocs)
        if self.iocs_v2:
            self._iocs_v2 = [IOC_V2(cb, initial_data=ioc) for ioc in self.iocs_v2]

    def validate(self):
        super(Report, self).validate()

        if self.link and not validators.url(self.link):
            raise InvalidObjectError("link should be a valid URL")

    def update(self, **kwargs):
        if not self.id:
            raise ApiError("missing Report ID")
        if not self._feed_id:
            raise ApiError("missing Feed ID")

        for key, value in kwargs.items():
            if key in self._info:
                self._info[key] = value

        self.validate()

        new_info = self._cb.put_object("/threathunter/feedmgr/v1/feed/{}/report/{}".format(self._feed_id, self.id), self._info)
        self._info.update(new_info)
        return self

    def delete(self):
        if not self.id:
            raise ApiError("missing Report ID")
        if not self._feed_id:
            raise ApiError("missing Feed ID")

        self._cb.delete_object("/threathunter/feedmgr/v1/feed/{}/report/{}".format(self._feed_id, self.id))

    @property
    def iocs_(self):
        # NOTE(ww): This name is underscored because something in the model
        # hierarchy is messing up method resolution -- self.iocs and self.iocs_v2
        # are resolving to the attributes rather than the attribute-ified
        # methods.
        return self._iocs_v2


class IOCs(FeedModel):
    swagger_meta_file = "psc/threathunter/models/iocs.yaml"

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        if not initial_data:
            raise ApiError("IOCs can only be initialized from initial_data")

        super(IOCs, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                   force_init=force_init, full_doc=full_doc)


class IOC_V2(FeedModel):
    primary_key = "id"
    swagger_meta_file = "psc/threathunter/models/ioc_v2.yaml"

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        if not initial_data:
            raise ApiError("IOC_V2 can only be initialized from initial_data")

        super(IOC_V2, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                     force_init=force_init, full_doc=full_doc)

    def validate(self):
        super(IOCs, self).validate()

        if self.link and not validators.url(self.link):
            raise InvalidObjectError("link should be a valid URL")


class Watchlist(FeedModel):
    # NOTE(ww): Not documented.
    urlobject = "/threathunter/watchlistmgr/v2/watchlist"
    urlobject_single = "/threathunter/watchlistmgr/v2/watchlist/{}"
    swagger_meta_file = "psc/threathunter/models/watchlist.yaml"

    @classmethod
    def _query_implementation(cls, cb):
        return WatchlistQuery(cls, cb)

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        item = {}

        if initial_data:
            item = initial_data
        elif model_unique_id:
            # TODO(ww): It's probably bad practice to make a request here.
            # Maybe abstract this into a separate method?
            item = cb.get_object(self.urlobject_single.format(model_unique_id))

        feed_id = item.get("id")

        super(Watchlist, self).__init__(cb, model_unique_id=feed_id, initial_data=item,
                                        force_init=force_init, full_doc=full_doc)

    def save(self):
        self.validate()

        new_info = self._cb.post_object("/watchlistmgr/v2/watchlist", self._info).json()
        self._info.update(new_info)
        return self

    def validate(self):
        pass

    @property
    def classifier(self):
        classifier_dict = self._info.get("classifier")

        if not classifier_dict:
            return None

        return (classifier_dict["key"], classifier_dict["value"])

    def delete(self):
        if not self.id:
            raise ApiError("missing Watchlist ID")

        self._cb.delete_object("/watchlistmgr/v2/watchlist/{}".format(self.id))

    def enable_alerts(self):
        if not self.id:
            raise ApiError("missing Watchlist ID")

        self._cb.put_object("/watchlistmgr/v1/watchlist/{}/alert".format(self.id))

    def disable_alerts(self):
        if not self.id:
            raise ApiError("missing Watchlist ID")

        self._cb.delete_object("/watchlistmgr/v1/watchlist/{}/alert".format(self.id))

    def enable_tags(self):
        if not self.id:
            raise ApiError("missing Watchlist ID")

        self._cb.put_object("/watchlistmgr/v1/watchlist/{}/tag".format(self.id))

    def disable_tags(self):
        if not self.id:
            raise ApiError("missing Watchlist ID")

        self._cb.delete_object("/watchlistmgr/v1/watchlist/{}/tag".format(self.id))

    def reports(self):
        if not self.report_ids:
            return []

        for rep_id in self.report_ids:
            pass
