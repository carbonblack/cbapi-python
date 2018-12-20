from __future__ import absolute_import
from cbapi.errors import ApiError
from cbapi.models import NewBaseModel
import logging
from cbapi.psc.threathunter.query import Query, AsyncProcessQuery, TreeQuery


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
        """Returns a query for *Event*s associated with this process's process GUID.

        :param kwargs: Arguments to filter the event query with.
        :return: Returns a :py:class:`threathunter.rest_api.Query` object with the appropriate search parameters for events
        :rtype: :py:class:`threathunter.rest_api.Query`

        Example::

        >>> [print(event) for event in process.events()]
        >>> [print(event) for event in process.events(event_type="modload")]
        """
        return self._cb.select(Event).where(process_guid=self.process_guid).and_(**kwargs)

    def tree(self):
        """Returns a *Tree* of children (and possibly siblings) associated with this process.

        :return: Returns a :py:class:`Tree` object
        :rtype: :py:class:`Tree`

        Example:

        >>> tree = process.tree()
        """
        data = self._cb.select(Tree).where(process_guid=self.process_guid).all()
        return Tree(self._cb, initial_data=data)

    def parents(self):
        """Returns a query for parent processes associated with this process.

        :return: Returns a :py:class:`threathunter.rest_api.Query` object with the appropriate search parameters for parent processes
        :rtype: :py:class:`threathunter.rest_api.Query`
        """
        return self._cb.select(Process).where(process_guid=self.parent_guid)

    def children(self):
        """Returns a list of child processes for this process.

        :return: Returns a list of process objects
        :rtype: list of :py:class:`Process`
        """
        return self.tree().children()

    def siblings(self):
        # NOTE(ww): This shold be provided by the /tree endpoint eventually,
        # but currently isn't.
        raise ApiError("siblings() unimplemented")

    def feedhits(self):
        return self._cb.select(FeedHits).where(process_guid=self.process_guid)

    @property
    def process_md5(self):
        """Returns a string representation of the MD5 hash for this process.

        :return: A string representation of the process's MD5.
        :rtype: str
        """
        return next((hsh for hsh in self.process_hash if len(hsh) == 32), None)

    @property
    def process_sha256(self):
        """Returns a string representation of the SHA256 hash for this process.

        :return: A string representation of the process's SHA256.
        :rtype: str
        """
        return next((hsh for hsh in self.process_hash if len(hsh) == 64), None)

    def __repr__(self):
        return "<%s.%s: process id %s document id %s> @ %s" % (self.__class__.__module__, self.__class__.__name__,
                                                               self.process_guid, self.document_guid,
                                                               self._cb.session.server)


class Event(UnrefreshableModel):
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
    """Represents a process tree.
    """
    urlobject = '/pscr/query/v2/tree'
    primary_key = 'process_guid'

    @classmethod
    def _query_implementation(cls, cb):
        return TreeQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Tree, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                   force_init=force_init, full_doc=full_doc)

    def children(self):
        return [Process(self._cb, initial_data=child) for child in self.nodes["children"]]
