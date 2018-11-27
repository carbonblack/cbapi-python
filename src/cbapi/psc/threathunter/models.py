from __future__ import absolute_import
from cbapi.models import NewBaseModel
import logging
from cbapi.psc.threathunter.query import Query, AsyncProcessQuery, TreeQuery, FeedHitsQuery


log = logging.getLogger(__name__)


class Process(NewBaseModel):
    # TODO(ww): Currently unused; should we be using this?
    urlobject = '/api/v1/process'
    default_sort = 'last_update desc'
    primary_key = "process_guid"

    @classmethod
    def _query_implementation(cls, cb):
        # This will emulate a synchronous process query, for now.
        return AsyncProcessQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Process, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                      force_init=force_init, full_doc=full_doc)

    def events(self):
        return self._cb.select(Events).where(process_guid=self.process_guid)

    def tree(self):
        return self._cb.select(Tree).where(process_guid=self.process_guid)

    # TODO(ww): /pscr/query/v1/evaluate takes the results of this call
    def feedhits(self):
        return self._cb.select(FeedHits).where(process_guid=self.process_guid)


class Events(NewBaseModel):
    urlobject = '/pscr/query/v1/events'
    default_sort = 'last_update desc'
    primary_key = "process_guid"

    @classmethod
    def _query_implementation(cls, cb):
        return Query(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Events, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                     force_init=force_init, full_doc=full_doc)


class Tree(NewBaseModel):
    urlobject = '/pscr/query/v1/tree'
    primary_key = 'process_guid'

    @classmethod
    def _query_implementation(cls, cb):
        return TreeQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Tree, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                   force_init=force_init, full_doc=full_doc)


class FeedHits(NewBaseModel):
    urlobject = '/pscr/query/v1/feedhits'
    primary_key = 'process_guid'

    @classmethod
    def _query_implementation(cls, cb):
        return FeedHitsQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(FeedHits, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                       force_init=force_init, full_doc=full_doc)
