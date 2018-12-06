from cbapi.query import PaginatedQuery, BaseQuery
from cbapi.errors import ServerError, ApiError
import time
from solrq import Q
from six import string_types
import logging


log = logging.getLogger(__name__)


class QueryBuilder(object):
    """
    Provides a flexible interface for building prepared queries for the CB
    ThreatHunter backend.

    This object can be instantiated directly, or can be managed implicitly
    through the :py:meth:`CbThreatHunterAPI.select` API.

    Examples::

    >>> from cbapi.psc.threathunter import QueryBuilder
    >>> # build a query with chaining
    >>> query = QueryBuilder().where(process_name="malicious.exe").and_(device_name="suspect")
    >>> # start with an initial query, and chain another condition to it
    >>> query = QueryBuilder(device_os="WINDOWS").or_(process_username="root")

    """
    # TODO(ww): Facet methods.
    def __init__(self, **kwargs):
        if kwargs:
            self._query = Q(**kwargs)
        else:
            self._query = None
        self._raw_query = None
        self._process_guid = None

    def _guard_query_change(self):
        if self._raw_query is not None:
            raise ApiError("Cannot modify a solrq.Q query with a raw query")

    def _guard_raw_query_change(self):
        if self._query is not None:
            raise ApiError("Cannot modify a raw query with a solrq.Q query")

    def where(self, q, **kwargs):
        if isinstance(q, string_types):
            self._guard_raw_query_change()
            if self._raw_query is None:
                self._raw_query = []
            self._raw_query.append(q)
        elif isinstance(q, Q) or kwargs:
            self._guard_query_change()
            if self._query is not None:
                raise ApiError("Use .and_() or .or_() for an extant solrq.Q object")
            if kwargs:
                self._process_guid = self._process_guid or kwargs.get("process_guid")
                q = Q(**kwargs)
            self._query = q
        else:
            raise ApiError(".where() only accepts strings or solrq.Q objects")

        return self

    def and_(self, q, **kwargs):
        if isinstance(q, string_types):
            self.where(q)
        else:
            self._guard_query_change()
            if kwargs:
                self._process_guid = self._process_guid or kwargs.get("process_guid")
                q = Q(**kwargs)
            if self._query is None:
                self._query = q
            else:
                self._query = self._query & q

        return self

    def or_(self, q, **kwargs):
        if kwargs:
            self._process_guid = self._process_guid or kwargs.get("process_guid")
            q = Q(**kwargs)

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

    This object is returned as part of a :py:meth:`CbThreatHunterPI.select`
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

    def where(self, q=None, **kwargs):
        """Add a filter to this query.

        :param str q: Query string, :py:class:`QueryBuilder`, or solrq.Q object
        :param kwargs: Arguments to construct a solrq.Q with
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if not q and not kwargs:
            raise ApiError(".where() expects a string, a QueryBuilder, a solrq.Q, or kwargs")

        if isinstance(q, QueryBuilder):
            self._query_builder = q
        else:
            self._query_builder.where(q, **kwargs)
        return self

    def and_(self, q=None, **kwargs):
        """Add a conjunctive filter to this query.

        :param str q: Query string or solrq.Q object
        :param kwargs: Arguments to construct a solrq.Q with
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if not q and not kwargs:
            raise ApiError(".and_() expects a string, a solrq.Q, or kwargs")

        self._query_builder.and_(q, **kwargs)
        return self

    def or_(self, q=None, **kwargs):
        """Add a disjunctive filter to this query.

        :param str q: solrq.Q object
        :param kwargs: Arguments to construct a solrq.Q with
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if not q and not kwargs:
            raise ApiError(".or_() expects a solrq.Q, or kwargs")

        self._query_builder.or_(q, **kwargs)
        return self

    def _get_query_parameters(self):
        args = self._default_args.copy()
        args['q'] = self._query_builder.collapse()
        args["cb.process_guid"] = self._query_builder._process_guid

        return args

    def _count(self):
        args = {"search_params": self._get_query_parameters()}

        log.info("args: {}".format(str(args)))

        self._total_results = int(self._cb.post_object(self._doc_class.urlobject, body=args)
                                  .json().get("response_header", {}).get("num_found", 0))
        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = self._get_query_parameters()

        validated = self._cb.get_object("/pscr/query/v1/validate", query_parameters=args)

        if not validated.get("valid"):
            raise ApiError("Invalid query: {}".format(args))

        if start != 0:
            args['start'] = start
        args['rows'] = self._batch_size

        args = {"search_params": args}

        current = start
        numrows = 0

        still_querying = True

        while still_querying:
            resp = self._cb.post_object(self._doc_class.urlobject, body=args)
            result = resp.json()

            self._total_results = result.get("response_header", {}).get("num_found", 0)
            self._count_valid = True

            results = result.get('docs', [])

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
        self._timeout = 0
        self._timed_out = False

    def timeout(self, msecs):
        self._timeout = msecs
        return self

    def submit(self):
        if self._query_token:
            raise ApiError("Query already submitted: token {0}".format(self._query_token))

        args = self._get_query_parameters()

        validated = self._cb.get_object("/pscr/query/v1/validate", query_parameters=args)

        if not validated.get("valid"):
            raise ApiError("Invalid query: {}".format(args))

        query_start = self._cb.post_object("/pscr/query/v1/start", body={"search_params": args})

        # TODO(ww): Is this still needed, now that we check for errorMessage
        # in api_json_request?
        if query_start.json().get("status_code") != 200:
            raise ServerError(query_start.status_code, query_start.json().get("message"))

        self._query_token = query_start.json().get("query_id")
        self._timed_out = False
        self._submit_time = time.time() * 1000

    def _still_querying(self):
        if not self._query_token:
            self.submit()

        args = {"query_id": self._query_token}

        result = self._cb.get_object("/pscr/query/v1/status", query_parameters=args)

        if result.get("status_code") != 200:
            raise ServerError(result["status_code"], result["errorMessage"])

        searchers_contacted = result.get("contacted", 0)
        searchers_completed = result.get("completed", 0)
        log.info("contacted = {}, completed = {}".format(searchers_contacted, searchers_completed))
        if searchers_contacted == 0:
            return True
        if searchers_completed < searchers_contacted:
            if self._timeout != 0 and (time.time() * 1000) - self._submit_time > self._timeout:
                self._timed_out = True
                # TODO(ww): Maybe raise here instead of returning?
                return False
            return True

        return False

    def _count(self):
        if self._count_valid:
            return self._total_results

        # TODO(ww): Do we need to reset self._submit_time here?
        while self._still_querying():
            time.sleep(.5)

        if self._timed_out:
            raise ApiError("user-specified timeout exceeded while waiting for results")

        args = {"query_id": self._query_token, "row_count": 0}

        result = self._cb.get_object("/pscr/query/v1/results",
                                     query_parameters=args)

        self._total_results = result.get('response_header', {}).get('num_found', 0)
        self._count_valid = True

        return self._total_results

    def _search(self, start=0, rows=0):
        if not self._query_token:
            self.submit()

        query_id = {"query_id": self._query_token}

        while self._still_querying():
            time.sleep(.5)

        if self._timed_out:
            raise ApiError("user-specified timeout exceeded while waiting for results")

        log.info("Pulling results, timed_out={}".format(self._timed_out))
        result = self._cb.get_object("/pscr/query/v1/results", query_parameters=query_id)
        results = result.get('data', [])

        self._total_results = result.get('response_header', {}).get('num_found', 0)
        self._count_valid = True

        # TODO: implement pagination
        for item in results:
            yield item


class TreeQuery(BaseQuery):
    def __init__(self, doc_class, cb):
        super(TreeQuery, self).__init__()
        self._doc_class = doc_class
        self._cb = cb
        self._args = {}

    # TODO(ww): Instead of reimplementing these, we could probably
    # make the QueryBuilder class more flexible. Maybe allow it to store
    # a dict internally, in addition to the Q and string options?
    def where(self, **kwargs):
        self._args = dict(self._args, **kwargs)
        return self

    def and_(self, **kwargs):
        self.where(**kwargs)
        return self

    def or_(self, **kwargs):
        raise ApiError(".or_() cannot be called on Tree queries")

    def _perform_query(self):
        if "process_guid" not in self._args:
            raise ApiError("required parameter process_guid missing")

        log.info("Fetching process tree")

        result = self._cb.get_object(self._doc_class.urlobject, query_parameters=self._args)

        return result


class FeedHitsQuery(Query):
    def __init__(self, doc_class, cb):
        super(FeedHitsQuery, self).__init__(doc_class, cb)
        self._args = {}

    # TODO(ww): Instead of reimplementing these, we could probably
    # make the QueryBuilder class more flexible. Maybe allow it to store
    # a dict internally, in addition to the Q and string options?
    def where(self, **kwargs):
        self._args = dict(self._args, **kwargs)
        return self

    def and_(self, **kwargs):
        self.where(**kwargs)
        return self

    def or_(self, **kwargs):
        raise ApiError(".or_() cannot be called on FeedHits queries")

    def _search(self, start=0, rows=0):
        if "process_guid" not in self._args:
            raise ApiError("required parameter process_guid missing")

        log.info("Fetching feed hits")

        # TODO(ww): This endpoint responds with 200, but consistently returns a JSON
        # blob indicating 404. Is it down?
        result = self._cb.get_object(self._doc_class.urlobject, query_parameters=self._args)
        log.info(str(result))
        feed_hits = result.get("feed_hits", [])

        for feed_hit in feed_hits:
            yield feed_hit
