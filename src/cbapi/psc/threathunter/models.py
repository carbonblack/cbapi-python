from __future__ import absolute_import
from cbapi.errors import ApiError
from cbapi.models import NewBaseModel, CreatableModelMixin
import logging
from cbapi.psc.threathunter.query import Query, AsyncProcessQuery, TreeQuery, FeedQuery, ReportQuery


log = logging.getLogger(__name__)


class UnrefreshableModel(NewBaseModel):
    """Represents a model that can't be refreshed, i.e. for which ``reset()``
    is not a valid operation.
    """
    def refresh(self):
        raise ApiError("refresh() called on an unrefreshable model")


class Process(UnrefreshableModel):
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


class Event(UnrefreshableModel):
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


class Tree(UnrefreshableModel):
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


class Feed(UnrefreshableModel, CreatableModelMixin):
    """Represents a ThreatHunter feed's metadata.
    """
    urlobject = "/threathunter/feedmgr/v1/feed"
    primary_key = "id"

    @classmethod
    def _query_implementation(cls, cb):
        return FeedQuery(cls, cb)

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        item = None

        if initial_data:
            item = initial_data
        elif model_unique_id:
            # TODO(ww): It's probably bad practice to make a request here.
            # Maybe abstract this into a separate method?
            resp = cb.get_object("/threathunter/feedmgr/v1/feed/{}".format(model_unique_id))
            # NOTE(ww): This strips the reports from the resultant Feed model.
            # Maybe store them in self._reports and return them from self.reports()?
            item = resp.get("feedinfo", {})

        if not item:
            raise ApiError("missing either model_unique_id or initial_data")

        super(Feed, self).__init__(cb, model_unique_id=item["id"], initial_data=item,
                                   force_init=force_init, full_doc=full_doc)

    def _validate(self):
        pass

    def delete(self):
        if not self.id:
            raise ApiError("missing Feed ID")

        self._cb.delete_object("/threathunter/feedmgr/v1/feed/{}".format(self.id))

    def reports(self):
        return self._cb.select(Report).where(feed_id=self.id)

    def replace(self):
        pass


class Report(UnrefreshableModel, CreatableModelMixin):
    """Represents reports retrieved from a ThreatHunter feed.
    """
    urlobject = "/threathunter/feedmgr/v1/feed/{}/report"
    primary_key = "id"

    @classmethod
    def _query_implementation(cls, cb):
        return ReportQuery(cls, cb)

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Report, self).__init__(cb, model_unique_id=initial_data["id"], initial_data=initial_data,
                                     force_init=force_init, full_doc=full_doc)

        self._iocs = self.iocs
        self._iocs_v2 = self._iocs_v2

    def _validate(self):
        pass

    def delete(self):
        if not self.id:
            raise ApiError("missing Report ID")

        # TODO(ww): Problem: Report deletion requires the feed ID.
        # self._cb.delete_object("/threathunter/feedmgr/v1/feed/")

    def iocs(self):
        pass


class Watchlist(UnrefreshableModel):
    pass


class IOC(UnrefreshableModel):
    primary_key = "id"

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        if not initial_data:
            raise ApiError("IOC can only be initialized from initial_data")

        super(Report, self).__init__(cb, model_unique_id=initial_data["id"], initial_data=initial_data,
                                     force_init=force_init, full_doc=full_doc)

    def _validate(self):
        pass
    pass
