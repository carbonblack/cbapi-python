from cbapi.query import PaginatedQuery, BaseQuery
from cbapi.utils import convert_query_params
from cbapi.errors import ServerError, ApiError
import time
from solrq import Q
from six import string_types
import logging


log = logging.getLogger(__name__)


class QueryBuilder(object):
    # TODO(ww): Facet methods?
    def __init__(self):
        self._query = None
        self._raw_query = None

    def _guard_query_change(self):
        if self._raw_query is not None:
            raise ApiError("Cannot modify a solrq.Q query with a raw query")

    def _guard_raw_query_change(self):
        if self._query is not None:
            raise ApiError("Cannot modify a raw query with a solrq.Q query")

    def where(self, q):
        if isinstance(q, string_types):
            self._guard_raw_query_change()
            if self._raw_query is None:
                self._raw_query = []
            self._raw_query.append(q)
        elif isinstance(q, Q):
            self._guard_query_change()
            if self._query is not None:
                raise ApiError("Use .and_() or .or_() for an extant solrq.Q object")
            self._query = q
        else:
            raise ApiError(".where() only accepts strings or solrq.Q objects")

        return self

    def and_(self, q):
        if isinstance(q, string_types):
            self.where(q)
        else:
            self._guard_query_change()
            if self._query is None:
                self._query = q
            else:
                self._query = self._query & q

        return self

    def or_(self, q):
        if isinstance(q, Q):
            self._guard_query_change()
            if self._query is None:
                self._query = q
            else:
                self._query = self._query | q
        else:
            raise ApiError(".or_() only accepts solrq.Q objects")

        return self

    def collapse(self):
        """The query can be represented by either an array of strings
        (_raw_query) which is concatenated and passed directly to Solr, or
        a solrq.Q object (_query) which is then converted into a string to
        pass to Solr. This function will perform the appropriate conversions to
        end up with the 'q' string sent into the POST request to the
        PSC-R query endpoint."""
        if self._raw_query is not None:
            return " ".join(self._raw_query)
        elif self._query is not None:
            return str(self._query)
        else:
            return "*:*"               # return everything


class QueryResults(BaseQuery):
    def __init__(self, cb, query_id):
        super(QueryResults, self).__init__()
        self._cb = cb
        self._query_id = query_id

    def _search(self, start=0, rows=0):
        pass


class Query(PaginatedQuery):
    """Represents a prepared query to the Cb ThreatHunter backend.

    This object is returned as part of a :py:meth:`CbResponseAPI.select`
    operation on models requested from the Cb ThreatHunter backend. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    Examples::

    >>> from cbapi.psc.threathunter import CbThreatHunterAPI
    >>> cb = CbThreatHunterAPI()

    Notes:
        - The slicing operator only supports start and end parameters, but not step. ``[1:-1]`` is legal, but
          ``[1:2:-1]`` is not.
        - You can chain where clauses together to create AND queries; only objects that match all ``where`` clauses
          will be returned.
    """

    def __init__(self, doc_class, cb):
        super(Query, self).__init__(doc_class, cb, None)

        self._query_builder = QueryBuilder()
        self._sort_by = None
        self._group_by = None
        self._batch_size = 100
        self._default_args = {}

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        nq._sort_by = self._sort_by
        nq._group_by = self._group_by
        nq._batch_size = self._batch_size
        return nq

    def where(self, q):
        """Add a filter to this query.

        :param str q: Query string or solrq.Q object
        :return: Query object
        :rtype: :py:class:`Query`
        """
        self._query_builder.where(q)
        return self

    def and_(self, q):
        """Add a filter to this query. Equivalent to calling :py:meth:`where` on this object.

        :param str q: Query string or solrq.Q object
        :return: Query object
        :rtype: :py:class:`Query`
        """
        self._query_builder.and_(q)
        return self

    def or_(self, q):
        """Add a disjunctive filter to this query.

        :param str q: solrq.Q object
        :return: Query object
        :rtype: :py:class:`Query`
        """
        self._query_builder.or_(q)
        return self

    def _get_query_parameters(self):
        args = self._default_args.copy()
        args['q'] = self._query_builder.collapse()

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


class AsyncProcessQuery(Query):
    def __init__(self, doc_class, cb):
        super(AsyncProcessQuery, self).__init__(doc_class, cb)
        self._query_token = None

    def submit(self):
        if self._query_token:
            raise ApiError("Query already submitted: token {0}".format(self._query_token))

        args = self._get_query_parameters()

        query_start = self._cb.post_object("/pscr/query/v1/start", body={"search_params": args})

        if query_start.json().get("status_code") != 200:
            raise ServerError(query_start.status_code, query_start.json().get("message"))

        log.info("Received response from /query/start: {0}".format(query_start.json()))
        self._query_token = query_start.json().get("query").get("cb.query_id")

    def _search(self, start=0, rows=0):
        if not self._query_token:
            self.submit()

        still_querying = True
        query_id = convert_query_params({"query_id": self._query_token})

        while still_querying:
            time.sleep(.5)
            result = self._cb.get_object("/pscr/query/v1/status", query_parameters=query_id)

            if result.get("status_code") != 200:
                raise ServerError(result.status_code, result.json().get("message"))

            searchers_contacted = result.get("contacted", 0)
            searchers_completed = result.get("completed", 0)
            log.info("contacted = {}, completed = {}".format(searchers_contacted, searchers_completed))
            if searchers_contacted == 0:
                continue
            if searchers_completed < searchers_contacted:
                continue

            still_querying = False
            self._count_valid = True

            log.info("Pulling results")
            result = self._cb.get_object("/pscr/query/v1/results", query_parameters=query_id)
            results = result.get('data', [])

            # TODO: implement pagination
            for item in results:
                yield item
