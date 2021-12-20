from cbapi.query import PaginatedQuery, BaseQuery, SimpleQuery
from cbapi.errors import ApiError, TimeoutError
import time
from solrq import Q
from six import string_types
import logging
import functools


log = logging.getLogger(__name__)


class QueryBuilder(object):
    """
    Provides a flexible interface for building prepared queries for the Carbon Black
    Enterprise EDR backend.

    This object can be instantiated directly, or can be managed implicitly
    through the :py:meth:`CbThreatHunterAPI.select` API.

    Examples::

    >>> from cbapi.psc.threathunter import QueryBuilder
    >>> # build a query with chaining
    >>> query = QueryBuilder().where(process_name="malicious.exe").and_(device_name="suspect")
    >>> # start with an initial query, and chain another condition to it
    >>> query = QueryBuilder(device_os="WINDOWS").or_(process_username="root")

    """
    def __init__(self, **kwargs):
        if kwargs:
            self._query = Q(**kwargs)
        else:
            self._query = None
        self._raw_query = None
        self._process_guid = None

    def _guard_query_params(func):
        """Decorates the query construction methods of *QueryBuilder*, preventing
        them from being called with parameters that would result in an intetnally
        inconsistent query.
        """
        @functools.wraps(func)
        def wrap_guard_query_change(self, q, **kwargs):
            if self._raw_query is not None and (kwargs or isinstance(q, Q)):
                raise ApiError("Cannot modify a raw query with structured parameters")
            if self._query is not None and isinstance(q, string_types):
                raise ApiError("Cannot modify a structured query with a raw parameter")
            return func(self, q, **kwargs)
        return wrap_guard_query_change

    @_guard_query_params
    def where(self, q, **kwargs):
        """Adds a conjunctive filter to a query.

        :param q: string or `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: QueryBuilder object
        :rtype: :py:class:`QueryBuilder`
        """
        if isinstance(q, string_types):
            if self._raw_query is None:
                self._raw_query = []
            self._raw_query.append(q)
        elif isinstance(q, Q) or kwargs:
            if self._query is not None:
                raise ApiError("Use .and_() or .or_() for an extant solrq.Q object")
            if kwargs:
                self._process_guid = self._process_guid or kwargs.get("process_guid")
                q = Q(**kwargs)
            self._query = q
        else:
            raise ApiError(".where() only accepts strings or solrq.Q objects")

        return self

    @_guard_query_params
    def and_(self, q, **kwargs):
        """Adds a conjunctive filter to a query.

        :param q: string or `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: QueryBuilder object
        :rtype: :py:class:`QueryBuilder`
        """
        if isinstance(q, string_types):
            self.where(q)
        elif isinstance(q, Q) or kwargs:
            if kwargs:
                self._process_guid = self._process_guid or kwargs.get("process_guid")
                q = Q(**kwargs)
            if self._query is None:
                self._query = q
            else:
                self._query = self._query & q
        else:
            raise ApiError(".and_() only accepts strings or solrq.Q objects")

        return self

    @_guard_query_params
    def or_(self, q, **kwargs):
        """Adds a disjunctive filter to a query.

        :param q: `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: QueryBuilder object
        :rtype: :py:class:`QueryBuilder`
        """
        if kwargs:
            self._process_guid = self._process_guid or kwargs.get("process_guid")
            q = Q(**kwargs)

        if isinstance(q, Q):
            if self._query is None:
                self._query = q
            else:
                self._query = self._query | q
        else:
            raise ApiError(".or_() only accepts solrq.Q objects")

        return self

    @_guard_query_params
    def not_(self, q, **kwargs):
        """Adds a negative filter to a query.

        :param q: `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: QueryBuilder object
        :rtype: :py:class:`QueryBuilder`
        """
        if kwargs:
            q = ~ Q(**kwargs)

        if isinstance(q, Q):
            if self._query is None:
                self._query = q
            else:
                self._query = self._query & q
        else:
            raise ApiError(".not_() only accepts solrq.Q objects")

    def _collapse(self):
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


class Query(PaginatedQuery):
    """Represents a prepared query to the Carbon Black Enterprise EDR backend.

    This object is returned as part of a :py:meth:`CbThreatHunterPI.select`
    operation on models requested from the Enterprise EDR backend. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    Examples::

    >>> from cbapi.psc.threathunter import CbThreatHunterAPI,Process
    >>> cb = CbThreatHunterAPI()
    >>> query = cb.select(Process)
    >>> query = query.where(process_name="notepad.exe")
    >>> # alternatively:
    >>> query = query.where("process_name:notepad.exe")

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

    def where(self, q=None, **kwargs):
        """Add a filter to this query.

        :param q: Query string, :py:class:`QueryBuilder`, or `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
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

        :param q: Query string or `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if not q and not kwargs:
            raise ApiError(".and_() expects a string, a solrq.Q, or kwargs")

        self._query_builder.and_(q, **kwargs)
        return self

    def or_(self, q=None, **kwargs):
        """Add a disjunctive filter to this query.

        :param q: `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if not q and not kwargs:
            raise ApiError(".or_() expects a solrq.Q or kwargs")

        self._query_builder.or_(q, **kwargs)
        return self

    def not_(self, q=None, **kwargs):
        """Adds a negated filter to this query.

        :param q: `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: Query object
        :rtype: :py:class:`Query`
        """

        if not q and not kwargs:
            raise ApiError(".not_() expects a solrq.Q, or kwargs")

        self._query_builder.not_(q, **kwargs)
        return self

    def _get_query_parameters(self):
        args = self._default_args.copy()
        args['query'] = self._query_builder._collapse()
        if self._query_builder._process_guid is not None:
            args["process_guid"] = self._query_builder._process_guid
        args["fields"] = [
            "*",
            "parent_hash",
            "parent_name",
            "process_cmdline",
            "backend_timestamp",
            "device_external_ip",
            "device_group",
            "device_internal_ip",
            "device_os",
            "device_policy",
            "process_effective_reputation",
            "process_reputation",
            "process_start_time",
            "ttp"
        ]

        return args

    def _count(self):
        args = self._get_query_parameters()

        log.debug("args: {}".format(str(args)))

        result = self._cb.post_object(
            self._doc_class.urlobject.format(
                self._cb.credentials.org_key,
                args["process_guid"]
            ), body=args
        ).json()

        self._total_results = int(result.get('num_available', 0))
        self._count_valid = True

        return self._total_results

    def _validate(self, args):
        if not self._doc_class.validation_url:
            return

        url = self._doc_class.validation_url.format(self._cb.credentials.org_key)

        if args.get('query', False):
            args['q'] = args['query']

        # v2 search sort key does not work with v1 validation
        args.pop('sort', None)

        validated = self._cb.get_object(url, query_parameters=args)

        if not validated.get("valid"):
            raise ApiError("Invalid query: {}: {}".format(args, validated["invalid_message"]))

    def _search(self, start=0, rows=0):
        # iterate over total result set, 100 at a time
        args = self._get_query_parameters()
        self._validate(args)

        if start != 0:
            args['start'] = start
        args['rows'] = self._batch_size

        # args = {"search_params": args}

        current = start
        numrows = 0

        still_querying = True

        while still_querying:
            url = self._doc_class.urlobject.format(
                self._cb.credentials.org_key,
                args["process_guid"]
            )
            resp = self._cb.post_object(url, body=args)
            result = resp.json()

            self._total_results = result.get("num_available", 0)
            self._total_segments = result.get("total_segments", 0)
            self._processed_segments = result.get("processed_segments", 0)
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
    """Represents the query logic for an asychronous Process query.

    This class specializes :py:class:`Query` to handle the particulars of
    process querying.
    """
    def __init__(self, doc_class, cb):
        super(AsyncProcessQuery, self).__init__(doc_class, cb)
        self._query_token = None
        self._timeout = 0
        self._timed_out = False
        self._sort = []

    def sort_by(self, key, direction="ASC"):
        """Sets the sorting behavior on a query's results.

        Example::

        >>> cb.select(Process).where(process_name="cmd.exe").sort_by("device_timestamp")

        :param key: the key in the schema to sort by
        :param direction: the sort order, either "ASC" or "DESC"
        :rtype: :py:class:`AsyncProcessQuery`
        """
        found = False

        for sort_item in self._sort:
            if sort_item['field'] == key:
                sort_item['order'] = direction
                found = True

        if not found:
            self._sort.append({'field': key, 'order': direction})

        self._default_args['sort'] = self._sort

        return self

    def timeout(self, msecs):
        """Sets the timeout on a process query.

        Example::

        >>> cb.select(Process).where(process_name="foo.exe").timeout(5000)

        :param: msecs: the timeout duration, in milliseconds
        :return: AsyncProcessQuery object
        :rtype: :py:class:`AsyncProcessQuery`
        """
        self._timeout = msecs
        return self

    def _submit(self):
        if self._query_token:
            raise ApiError("Query already submitted: token {0}".format(self._query_token))

        args = self._get_query_parameters()
        args['rows'] = 10000
        self._validate(args)

        url = "/api/investigate/v2/orgs/{}/processes/search_jobs".format(self._cb.credentials.org_key)
        query_start = self._cb.post_object(url, body=args)

        self._query_token = query_start.json().get("job_id")

        self._timed_out = False
        self._submit_time = time.time() * 1000

    def _still_querying(self):
        if not self._query_token:
            self._submit()

        status_url = "/api/investigate/v1/orgs/{}/processes/search_jobs/{}".format(
            self._cb.credentials.org_key,
            self._query_token,
        )
        result = self._cb.get_object(status_url)

        searchers_contacted = result.get("contacted", 0)
        searchers_completed = result.get("completed", 0)
        log.debug("contacted = {}, completed = {}".format(searchers_contacted, searchers_completed))
        if searchers_contacted == 0:
            return True
        if searchers_completed < searchers_contacted:
            if self._timeout != 0 and (time.time() * 1000) - self._submit_time > self._timeout:
                self._timed_out = True
                return False
            return True

        return False

    def _count(self):
        if self._count_valid:
            return self._total_results

        while self._still_querying():
            time.sleep(.5)

        if self._timed_out:
            raise TimeoutError(message="user-specified timeout exceeded while waiting for results")

        result_url = "/api/investigate/v2/orgs/{}/processes/search_jobs/{}/results".format(
            self._cb.credentials.org_key,
            self._query_token,
        )
        result = self._cb.get_object(result_url)

        self._total_results = result.get('num_available', 0)
        self._count_valid = True

        return self._total_results

    def _search(self, start=0, rows=0):
        if not self._query_token:
            self._submit()

        while self._still_querying():
            time.sleep(.5)

        if self._timed_out:
            raise TimeoutError(message="user-specified timeout exceeded while waiting for results")

        log.debug("Pulling results, timed_out={}".format(self._timed_out))

        current = start
        rows_fetched = 0
        still_fetching = True
        result_url_template = "/api/investigate/v2/orgs/{}/processes/search_jobs/{}/results".format(
            self._cb.credentials.org_key,
            self._query_token
        )
        query_parameters = {}
        while still_fetching:
            result_url = '{}?start={}&rows={}'.format(
                result_url_template,
                current,
                10  # Batch gets to reduce API calls
            )

            result = self._cb.get_object(result_url, query_parameters=query_parameters)

            self._total_results = result.get('num_available', 0)
            self._count_valid = True

            results = result.get('results', [])

            for item in results:
                yield item
                current += 1
                rows_fetched += 1

                if rows and rows_fetched >= rows:
                    still_fetching = False
                    break

            if current >= self._total_results:
                still_fetching = False

            log.debug("current: {}, total_results: {}".format(current, self._total_results))


class TreeQuery(BaseQuery):
    """ Represents the logic for a Tree query.
    """
    def __init__(self, doc_class, cb):
        super(TreeQuery, self).__init__()
        self._doc_class = doc_class
        self._cb = cb
        self._args = {}

    def where(self, **kwargs):
        """Adds a conjunctive filter to this *TreeQuery*.

        Example::

        >>> cb.select(Tree).where(process_guid="...")

        :param: kwargs: Arguments to invoke the *TreeQuery* with.
        :return: this *TreeQuery*
        :rtype: :py:class:`TreeQuery`
        """
        self._args = dict(self._args, **kwargs)
        return self

    def and_(self, **kwargs):
        """Adds a conjunctive filter to this *TreeQuery*.

        :param: kwargs: Arguments to invoke the *TreeQuery* with.
        :return: this *TreeQuery*
        :rtype: :py:class:`TreeQuery`
        """
        self.where(**kwargs)
        return self

    def or_(self, **kwargs):
        """Unsupported. Will raise if called.

        :raise: :py:class:`ApiError`
        """
        raise ApiError(".or_() cannot be called on Tree queries")

    def _perform_query(self):
        if "process_guid" not in self._args:
            raise ApiError("required parameter process_guid missing")

        log.debug("Fetching process tree")

        url = self._doc_class.urlobject.format(self._cb.credentials.org_key)
        results = self._cb.get_object(url, query_parameters=self._args)

        while results["incomplete_results"]:
            result = self._cb.get_object(url, query_parameters=self._args)
            results["nodes"]["children"].extend(result["nodes"]["children"])
            results["incomplete_results"] = result["incomplete_results"]

        return results


class FeedQuery(SimpleQuery):
    """Represents the logic for a :py:class:`Feed` query.

    >>> cb.select(Feed)
    >>> cb.select(Feed, id)
    >>> cb.select(Feed).where(include_public=True)
    """
    def __init__(self, doc_class, cb):
        super(FeedQuery, self).__init__(doc_class, cb)
        self._args = {}

    def where(self, **kwargs):
        self._args = dict(self._args, **kwargs)
        return self

    @property
    def results(self):
        log.debug("Fetching all feeds")
        url = self._doc_class.urlobject.format(self._cb.credentials.org_key)
        resp = self._cb.get_object(url, query_parameters=self._args)
        results = resp.get("results", [])
        return [self._doc_class(self._cb, initial_data=item) for item in results]


class ReportQuery(SimpleQuery):
    """Represents the logic for a :py:class:`Report` query.

    >>> cb.select(Report).where(feed_id=id)

    .. NOTE::
        Only feed reports can be queried. Watchlist reports
        should be interacted with via :py:meth:`Watchlist.reports`.
    """
    def __init__(self, doc_class, cb):
        super(ReportQuery, self).__init__(doc_class, cb)
        self._args = {}

    def where(self, **kwargs):
        self._args = dict(self._args, **kwargs)
        return self

    @property
    def results(self):
        if "feed_id" not in self._args:
            raise ApiError("required parameter feed_id missing")

        feed_id = self._args["feed_id"]

        log.debug("Fetching all reports")
        url = self._doc_class.urlobject.format(
            self._cb.credentials.org_key,
            feed_id,
        )
        resp = self._cb.get_object(url)
        results = resp.get("results", [])
        return [self._doc_class(self._cb, initial_data=item, feed_id=feed_id) for item in results]


class WatchlistQuery(SimpleQuery):
    """Represents the logic for a :py:class:`Watchlist` query.

    >>> cb.select(Watchlist)
    """
    def __init__(self, doc_class, cb):
        super(WatchlistQuery, self).__init__(doc_class, cb)

    @property
    def results(self):
        log.debug("Fetching all watchlists")

        resp = self._cb.get_object(self._doc_class.urlobject)
        results = resp.get("results", [])
        return [self._doc_class(self._cb, initial_data=item) for item in results]
