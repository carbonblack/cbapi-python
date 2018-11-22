from __future__ import absolute_import
from cbapi.models import NewBaseModel
import logging
from cbapi.psc.threathunter.query import AsyncProcessQuery


log = logging.getLogger(__name__)


class Process(NewBaseModel):
    urlobject = '/api/v1/process'
    default_sort = 'last_update desc'
    primary_key = "process_guid"

    @classmethod
    def _query_implementation(cls, cb):
        # This will emulate a synchronous process query, for now.
        return AsyncProcessQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=False):
        super(Process, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                      force_init=force_init, full_doc=full_doc)

    # TODO(ww): Fill these in
    def events(self):
        self._cb.get_object("")

    def tree(self):
        self._cb.get_object("")

    # TODO(ww): /pscr/query/v1/evaluate takes the results of this call
    def feedhits(self):
        self._cb.get_object("")
