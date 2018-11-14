from cbapi.query import PaginatedQuery, BaseQuery
from cbapi.utils import convert_query_params
from cbapi.errors import ServerError, ApiError
import time
from solrq import Q
from six import string_types
import logging


log = logging.getLogger(__name__)


class Query(PaginatedQuery):
    """Represents a prepared query to the Cb Resposne PSC backend.

    This object is returned as part of a :py:meth:`CbResponseAPI.select`
    operation on models requested from the Cb Response PSC backend. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    Examples::

    >>> from cbapi.psc.response import CbResponseAPI
    >>> cb = CbResponseAPI()

    Notes:
        - The slicing operator only supports start and end parameters, but not step. ``[1:-1]`` is legal, but
          ``[1:2:-1]`` is not.
        - You can chain where clauses together to create AND queries; only objects that match all ``where`` clauses
          will be returned.
    """

    def __init__(self, doc_class, cb):
        super(Query, self).__init__(doc_class, cb, None)

        self._query = None
        self._sort_by = None
        self._group_by = None
        self._batch_size = 100
        self._raw_query = None
        self._default_args = {}

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        if nq._query is not None:
            nq._query = self._query[::]
        else:
            nq._query = None
        nq._sort_by = self._sort_by
        nq._group_by = self._group_by
        nq._batch_size = self._batch_size
        return nq

    def where(self, q):
        """Add a filter to this query.

        :param str q: Query string
        :return: Query object
        :rtype: :py:class:`Query`
        """
        nq = self._clone()
        nq._query.append(q)
        return nq

    def and_(self, q):
        """Add a filter to this query. Equivalent to calling :py:meth:`where` on this object.

        :param str q: Query string
        :return: Query object
        :rtype: :py:class:`Query`
        """
        return self.where(q)

    def _get_query_parameters(self):
        if self._raw_query:
            args = self._raw_query.copy()
        else:
            args = self._default_args.copy()
            if self._query:
                args['q'] = self._query
            else:
                args['q'] = ''

        return args

    def _count(self):
        args = {'limit': 0}

        query_args = convert_query_params(args)
        self._total_results = int(self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)
                                  .get("totalResults", 0))
        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = self._get_query_parameters()
        if start != 0:
            args['start'] = start
        args['rows'] = self._batch_size

        current = start
        numrows = 0

        still_querying = True

        while still_querying:
            query_args = convert_query_params(args)
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

            args['start'] = current + 1  # as of 6/2017, the indexing on the Cb Defense backend is still 1-based

            if current >= self._total_results:
                break
            if not results:
                log.debug("server reported total_results overestimated the number of results for this query by {0}"
                          .format(self._total_results - current))
                log.debug("resetting total_results for this query to {0}".format(current))
                self._total_results = current
                break


# TODO: Split out the query object into a query builder and an iterator for the result set.
class QueryResults(BaseQuery):
    def __init__(self, cb, query_id):
        super(QueryResults, self).__init__()
        self._cb = cb
        self._query_id = query_id

    def _search(self, start=0, rows=0):
        pass



class SyncProcessQuery(Query):
    def __init__(self, doc_class, cb):
        super(SyncProcessQuery, self).__init__(doc_class, cb)

    def where(self, q):
        nq = self._clone()

        if isinstance(q, string_types):
            if nq._query is not None:
                raise ApiError("Cannot concatenate a raw query with a solrq query")
            if nq._raw_query is None:
                nq._raw_query = []
            nq._raw_query.append(q)
        elif isinstance(q, Q):
            if nq._raw_query is not None:
                raise ApiError("Cannot concatenate a solrq query with a raw query")
            if nq._query is not None:
                raise ApiError("Call .and_() or .or_() to add the solrq query")
            nq._query = q
        else:
            raise ApiError(".where() only accepts strings or solrq.Q objects")

        return nq

    def and_(self, q):
        nq = self._clone()

        if isinstance(q, string_types):
            if nq._raw_query is None:
                nq._raw_query = []
            nq._raw_query.append(q)
        elif isinstance(q, Q):
            if nq._query is None:
                nq._query = q
            else:
                nq._query = nq._query & q
        else:
            raise ApiError(".and_() only accepts strings or solrq.Q objects")

        return nq

    def or_(self, q):
        nq = self._clone()

        if isinstance(q, Q):
            if nq._query is None:
                nq._query = q
            else:
                nq._query = self._query | q
        else:
            raise ApiError(".or_() only accepts solrq.Q objects")

        return nq

    def collapse_query(self):
        """The query can be represented by either an array of strings (_raw_query) which is concatenated and
        passed directly to Solr, or
        a solrq.Q object (_query) which is then converted into a string to pass to Solr. This function will
        perform the appropriate conversions to end up with the 'q' string sent into the POST request to the
        PSC-R query endpoint."""
        if self._raw_query is not None:
            return " ".join(self._raw_query)
        elif self._query is not None:
            return str(self._query)
        else:
            return "*:*"               # return everything

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = self._get_query_parameters()
        # args["cb.full_docs"] = "true"

        # if start != 0:
        #     args['start'] = start
        # args['rows'] = self._batch_size
        #
        # current = start
        # numrows = 0

        log.info("args = {0}".format(args))
        still_querying = True
        args["q"] = self.collapse_query()

        query_start = self._cb.post_object("/integrationServices/v3/pscr/query/start", body=args)

        if not query_start.json().get("success"):
            raise ServerError(query_start.status_code, query_start.json().get("message"))

        log.info("Received response from /query/start: {0}".format(query_start.json()))
        query_token = query_start.json().get("query_id")

        still_querying = True
        while still_querying:
            time.sleep(.5)
            result = self._cb.post_object("/integrationServices/v3/pscr/query/results", body={"query_id": query_token})

            if not result.json().get("success"):
                raise ServerError(result.status_code, result.json().get("message"))

            # TODO: implement check to see if the search is complete or not
            query_meta = result.json().get("response_header", {})
            log.info("Query metadata = {0}".format(query_meta))
            if not query_meta:
                # TODO: this is a bug, we get 'success' but nothing else:
                # ipdb> result.json()
                # {'data': None, 'response_header': None, 'success': True, 'facets': None, 'message': None, 'query_id': None}
                continue

            self._count = query_meta.get("num_found", 0)
            query_meta = query_meta.get("searchers_meta", {})

            searchers_contacted = query_meta.get("contacted", 0)
            searchers_completed = query_meta.get("completed", 0)
            log.info("contacted = {}, completed = {}".format(searchers_contacted, searchers_completed))
            if searchers_contacted == 0:
                continue
            if searchers_completed < searchers_contacted:
                continue

            still_querying = False
            self._count_valid = True

            log.info("Pulling results")
            results = result.json().get('data', [])

            # TODO: implement pagination
            for item in results:
                yield item
