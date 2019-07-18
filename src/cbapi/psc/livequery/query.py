from cbapi.errors import ApiError, MoreThanOneResultError
import logging
import functools
from six import string_types
from solrq import Q

log = logging.getLogger(__name__)


class QueryBuilder(object):
    """
    Provides a flexible interface for building prepared queries for the CB
    LiveQuqery backend.

    This object can be instantiated directly, or can be managed implicitly
    through the :py:meth:`CbLiveQuqeryAPI.select` API.
    """

    def __init__(self, **kwargs):
        if kwargs:
            self._query = Q(**kwargs)
        else:
            self._query = None
        self._raw_query = None

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
            q = ~Q(**kwargs)

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
            return None  # return everything


class LiveQueryBase:
    """
    Represents the base of all LiveQuery query classes.
    """

    def __init__(self, doc_class, cb):
        self._doc_class = doc_class
        self._cb = cb


class IterableQueryMixin:
    """
    A mix-in to provide iterability to a query.
    """

    def all(self):
        return self._perform_query()

    def first(self):
        res = self[:1]
        if not len(res):
            return None
        return res[0]

    def one(self):
        res = self[:2]
        if len(res) == 0:
            raise MoreThanOneResultError(
                message="0 results for query {0:s}".format(self._query)
            )
        if len(res) > 1:
            raise MoreThanOneResultError(
                message="{0:d} results found for query {1:s}".format(
                    len(self), self._query
                )
            )
        return res[0]

    def __len__(self):
        return 0

    def __getitem__(self, item):
        return None

    def __iter__(self):
        return self._perform_query()


class RunQuery(LiveQueryBase):
    """
    Represents a query that either creates or retrieves the
    status of a LiveQuery run.
    """

    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_token = None
        self._query_body = {"device_filter": {}}
        self._device_filter = self._query_body["device_filter"]

    def device_ids(self, device_ids):
        """
        Restricts the devices that this LiveQuery run is performed on
        to the given IDs.

        :param device_ids: list of ints
        :return: This instance
        """
        if not all(isinstance(device_id, int) for device_id in device_ids):
            raise ApiError("One or more invalid device IDs")
        self._device_filter["device_ids"] = device_ids
        return self

    def device_types(self, device_types):
        """
        Restricts the devices that this LiveQuery run is performed on
        to the given device types.

        :param device_types: list of strs
        :return: This instance
        """
        if not all(isinstance(device_type, str) for device_type in device_types):
            raise ApiError("One or more invalid device types")
        self._device_filter["device_types"] = device_types
        return self

    def policy_ids(self, policy_ids):
        """
        Restricts this LiveQuery run to the given policy IDs.

        :param policy_ids: list of ints
        :return: This instance
        """
        if not all(isinstance(policy_id, int) for policy_id in policy_ids):
            raise ApiError("One or more invalid policy IDs")
        self._device_filter["policy_ids"] = policy_ids
        return self

    def where(self, sql):
        """
        Sets this LiveQuery run's underlying SQL.

        :param sql: The SQL to execute
        :return: This instance
        """
        self._query_body["sql"] = sql
        return self

    def name(self, name):
        """
        Sets this LiveQuery run's name. If no name is explicitly set,
        the run is named after its SQL.

        :param name: The run name
        :return: This instance
        """
        self._query_body["name"] = name
        return self

    def notify_on_finish(self):
        """
        Sets the notify-on-finish flag on this LiveQuery run.

        :return: This instance
        """
        self._query_body["notify_on_finish"] = True
        return self

    def submit(self):
        """
        Submits this LiveQuery run.

        :return: A new ``Run`` instance containing the run's status
        """
        if self._query_token is not None:
            raise ApiError(
                "Query already submitted: token {0}".format(self._query_token)
            )

        if "sql" not in self._query_body:
            raise ApiError("Missing LiveQuery SQL")

        url = self._doc_class.urlobject.format(self._cb.credentials.org_key)
        resp = self._cb.post_object(url, body=self._query_body)

        return self._doc_class(self._cb, initial_data=resp.json())


class ResultQuery(LiveQueryBase, IterableQueryMixin):
    """
    Represents a query that retrieves results from a LiveQuery run.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._criteria = {}
        self._sort = {}
        self._batch_size = 100
        self._run_id = None

    def where(self, q=None, **kwargs):
        """Add a filter to this query.

        :param q: Query string, :py:class:`QueryBuilder`, or `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if not q and not kwargs:
            raise ApiError(
                ".where() expects a string, a QueryBuilder, a solrq.Q, or kwargs"
            )

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

    def criteria(self, **kwargs):
        """Sets the filter criteria on a query's results.

        Example::

        >>> cb.select(Result).run_id(my_run).criteria(device_id=[123, 456])

        """
        self._criteria.update(kwargs)
        return self

    def sort_by(self, key, direction="ASC"):
        """Sets the sorting behavior on a query's results.

        Example::

        >>> cb.select(Result).run_id(my_run).where(username="foobar").sort_by("uid")

        :param key: the key in the schema to sort by
        :param direction: the sort order, either "ASC" or "DESC"
        :rtype: :py:class:`ResultQuery`
        """
        self._sort.update({"field": key, "order": direction})
        return self

    def run_id(self, run_id):
        """Sets the run ID to query results for.

        Example::

        >>> cb.select(Result).run_id(my_run)
        """
        self._run_id = run_id
        return self

    def _build_request(self, start, rows):
        request = {"start": start, "query": self._query_builder._collapse()}

        if rows != 0:
            request["rows"] = rows
        if self._criteria:
            request["criteria"] = self._criteria
        if self._sort:
            request["sort"] = [self._sort]

        return request

    def _count(self):
        if self._count_valid:
            return self._total_results

        if self._run_id is None:
            raise ApiError("Can't retrieve count without a run ID")

        url = self._doc_class.urlobject.format(
            self._cb.credentials.org_key, self._run_id
        )
        request = self._build_request(start=0, rows=0)
        resp = self._cb.post_object(url, body=request)
        result = resp.json()

        self._total_results = result["num_found"]
        self._count_valid = True

        return self._total_results

    def _perform_query(self, start=0, rows=0):
        if self._run_id is None:
            raise ApiError("Can't retrieve results without a run ID")

        url = self._doc_class.urlobject.format(
            self._cb.credentials.org_key, self._run_id
        )
        current = start
        numrows = 0
        still_querying = True
        while still_querying:
            request = self._build_request(start, rows)
            resp = self._cb.post_object(url, body=request)
            result = resp.json()

            self._total_results = result["num_found"]
            self._count_valid = True

            results = result.get("results", [])
            for item in results:
                yield self._doc_class(self._cb, item)
                current += 1
                numrows += 1

                if rows and numrows == rows:
                    still_querying = False
                    break

            start = current
            if current >= self._total_results:
                still_querying = False
                break
