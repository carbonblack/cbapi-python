from __future__ import absolute_import
from cbapi.errors import ApiError
from cbapi.models import NewBaseModel
import logging
from cbapi.psc.threathunter.query import Query, AsyncProcessQuery, TreeQuery, FeedHitsQuery


log = logging.getLogger(__name__)

class UnrefreshableModel(NewBaseModel):
    def refresh(self):
        raise ApiError("refresh() called on an unrefreshable model")

class Process(UnrefreshableModel):
    # TODO(ww): Currently unused; should we be using this?
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
        return self._cb.select(Events).where(process_guid=self.process_guid).and_(**kwargs)

    def tree(self):
        data = self._cb.select(Tree).where(process_guid=self.process_guid).all()
        return Tree(self._cb, initial_data=data)

    def children(self):
        return self.tree().children()

    def feedhits(self):
        return self._cb.select(FeedHits).where(process_guid=self.process_guid)

    def process_md5(self):
        return self.process_hash[0]

    def process_sha256(self):
        return self.process_hash[1]


class Events(UnrefreshableModel):
    urlobject = '/pscr/query/v1/events'
    validation_url = '/pscr/query/v1/events/validate'
    default_sort = 'last_update desc'
    primary_key = "process_guid"

    @classmethod
    def _query_implementation(cls, cb):
        return Query(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(Events, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                     force_init=force_init, full_doc=full_doc)


class Tree(UnrefreshableModel):
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


class FeedHits(UnrefreshableModel):
    urlobject = '/pscr/query/v1/feedhits'
    primary_key = 'process_guid'

    @classmethod
    def _query_implementation(cls, cb):
        return FeedHitsQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        super(FeedHits, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                       force_init=force_init, full_doc=full_doc)
