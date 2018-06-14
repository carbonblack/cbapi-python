from __future__ import absolute_import
from cbapi.psc.response.rest_api import Query, convert_query_params
from cbapi.errors import ServerError


class ProcessQuery(Query):
    def __init__(self, doc_class, cb, query=None):
        super(ProcessQuery, self).__init__(doc_class, cb, query)

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = {}
        args["cb.full_docs"] = "true"

        if start != 0:
            args['start'] = start
        args['rows'] = self._batch_size

        current = start
        numrows = 0

        args = self.prepare_query(args)
        still_querying = True

        while still_querying:
            query_args = convert_query_params(args)

            query_start = self._cb.post_object(self._doc_class.urlobject, query_parameters=query_args)

            if not query_start.json().get("success"):
                raise ServerError(query_start.status_code, query_start.json().get("message"))

            query_token = query_start.json().get("query_id")
            result = self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)

            self._total_results = result.get("totalResults", 0)
            self._count_valid = True

            results = result.get('results', [])

            for item in results:
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current + 1     # as of 6/2017, the indexing on the Cb Defense backend is still 1-based

            if current >= self._total_results:
                break
            if not results:
                log.debug("server reported total_results overestimated the number of results for this query by {0}"
                          .format(self._total_results - current))
                log.debug("resetting total_results for this query to {0}".format(current))
                self._total_results = current
                break
