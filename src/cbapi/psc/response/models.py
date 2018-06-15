from __future__ import absolute_import
from cbapi.psc.response.rest_api import Query, convert_query_params
from cbapi.errors import ServerError
from cbapi.models import NewBaseModel
import logging
import time


log = logging.getLogger(__name__)


class Process(NewBaseModel):
    urlobject = '/api/v1/process'
    default_sort = 'last_update desc'

    @classmethod
    def _query_implementation(cls, cb):
        # This will emulate a synchronous process query, for now.
        return SyncProcessQuery(cls, cb)

    def __init__(self, cb,  model_unique_id=None, initial_data=None, force_init=False, full_doc=False):
        super(Process, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                      force_init=force_init, full_doc=full_doc)


class SyncProcessQuery(Query):
    def __init__(self, doc_class, cb, query=None):
        super(SyncProcessQuery, self).__init__(doc_class, cb, query)

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = self._get_query_parameters()
        args["cb.full_docs"] = "true"

        if start != 0:
            args['start'] = start
        args['rows'] = self._batch_size

        current = start
        numrows = 0

        log.info("args = {0}".format(args))
        still_querying = True

        query_args = convert_query_params(args)

        query_start = self._cb.post_object("/integrationServices/v3/pscr/query/start", body=query_args)

        if not query_start.json().get("success"):
            raise ServerError(query_start.status_code, query_start.json().get("message"))

        query_token = query_start.json().get("query_id")

        while still_querying:
            time.sleep(.2)
            result = self._cb.post_object("/integrationServices/v3/pscr/query/results", body={"query_id": query_token})

            if not result.json().get("success"):
                raise ServerError(result.status_code, result.json().get("message"))

            # TODO: implement check to see if the search is complete or not
            query_meta = result.json().get("response_header", {})
            log.info("Query metadata = {0}".format(query_meta))

            results = result.json().get('data', [])

            # TODO: implement pagination
            for item in results:
                yield item
