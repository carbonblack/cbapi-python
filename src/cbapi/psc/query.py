from cbapi.errors import ApiError, MoreThanOneResultError
import logging
import functools
from six import string_types
from solrq import Q
from builtins import isinstance

log = logging.getLogger(__name__)

class QueryBuilder(object):
    """
    Provides a flexible interface for building prepared queries for the CB
    PSC backend.

    This object can be instantiated directly, or can be managed implicitly
    through the :py:meth:`select` API.
    """

    def __init__(self, **kwargs):
        if kwargs:
            self._query = Q(**kwargs)
        else:
            self._query = None
        self._raw_query = None

    def _guard_query_params(func):
        """Decorates the query construction methods of *QueryBuilder*, preventing
        them from being called with parameters that would result in an internally
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

class PSCQueryBase:
    """
    Represents the base of all LiveQuery query classes.
    """

    def __init__(self, doc_class, cb):
        self._doc_class = doc_class
        self._cb = cb


class QueryBuilderSupportMixin:
    """
    A mixin that supplies wrapper methods to access the _query_builder.
    """
    def where(self, q=None, **kwargs):
        """Add a filter to this query.

        :param q: Query string, :py:class:`QueryBuilder`, or `solrq.Q` object
        :param kwargs: Arguments to construct a `solrq.Q` with
        :return: Query object
        :rtype: :py:class:`Query`
        """

        if not q:
            return self
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
   

class IterableQueryMixin:
    """
    A mix-in to provide iterability to a query.
    """
    def all(self):
        return self._perform_query()

    def first(self):
        allres = list(self)
        res = allres[:1]
        if not len(res):
            return None
        return res[0]

    def one(self):
        allres = list(self)
        res = allres[:2]
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


class DeviceSearchQuery(PSCQueryBase, QueryBuilderSupportMixin, IterableQueryMixin):
    """
    Represents a query that is used to locate Device objects.
    """
    valid_statuses = ["PENDING", "REGISTERED", "UNINSTALLED", "DEREGISTERED",
                      "ACTIVE", "INACTIVE", "ERROR", "ALL", "BYPASS_ON",
                      "BYPASS", "QUARANTINE", "SENSOR_OUTOFDATE",
                      "DELETED", "LIVE"]
    valid_priorities = ["LOW", "MEDIUM", "HIGH", "MISSION_CRITICAL"]
    valid_sort_keys = ["target_priority", "policy_name", "name",
                       "last_contact_time", "av_pack_version"]
    valid_directions = ["ASC", "DESC"]
    
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._query_body = {}
        self._sortcriteria = {}
        
    def ad_group_ids(self, ad_group_ids):
        """
        Restricts the devices that this query is performed on to the specified
        AD group IDs.

        :param ad_group_ids: list of ints
        :return: This instance
        """
        if not all(isinstance(ad_group_id, int) for ad_group_id in ad_group_ids):
            raise ApiError("One or more invalid AD group IDs")
        self._query_body["ad_group_ids"] = ad_group_ids
        return self
    
    def policy_ids(self, policy_ids):
        """
        Restricts the devices that this query is performed on to the specified
        policy IDs.

        :param policy_ids: list of ints
        :return: This instance
        """
        if not all(isinstance(policy_id, int) for policy_id in policy_ids):
            raise ApiError("One or more invalid AD group IDs")
        self._query_body["policy_ids"] = policy_ids
        return self
        
    def status(self, statuses):
        """
        Restricts the devices that this query is performed on to the specified
        status values.

        :param statuses: list of strings
        :return: This instance
        """
        if not all((stat in DeviceSearchQuery.valid_statuses) for stat in statuses):
            raise ApiError("One or more invalid status values")
        self._query_body["status"] = statuses
        return self
    
    def target_priorities(self, target_priorities):
        """
        Restricts the devices that this query is performed on to the specified
        target priority values.

        :param target_priorities: list of strings
        :return: This instance
        """
        if not all((prio in DeviceSearchQuery.valid_priorities) for prio in target_priorities):
            raise ApiError("One or more invalid target priority values")
        self._query_body["target_priorities"] = target_priorities
        return self
    
    def sort_by(self, key, direction="ASC"):
        """Sets the sorting behavior on a query's results.

        Example::

        >>> cb.select(Device).sort_by("name")

        :param key: the key in the schema to sort by
        :param direction: the sort order, either "ASC" or "DESC"
        :rtype: :py:class:`DeviceSearchQuery`
        """
        if key not in DeviceSearchQuery.valid_sort_keys:
            raise ApiError("Invalid sort key specified")
        if direction not in DeviceSearchQuery.valid_directions:
            raise ApiError("invalid sort direction specified")
        self._sortcriteria = {"field_name": key, "sort_order": direction}
        return self
    
    def _build_request(self):
        request = self._query_body
        request["query_string"] = self._query_builder._collapse()
        if not self._sortcriteria.is_empty():
            request["sort"] = self._sortcriteria
        return request
    
    def _build_url(self, from_row, max_rows, tail_end):
        url = self._doc_class.urlobject.format(
            self._cb.credentials.org_key) + tail_end
        query_params = []
        if from_row > 0:
            query_params.append("from_row={0:i}".format(from_row))
        if max_rows >= 0:
            query_params.append("max_rows={0:i}".format(max_rows))
        if not query_params.is_empty():
            url = url + "?" + "&".join(query_params)
        return url
    
    def _count(self):
        if self._count_valid:
            return self._total_results
        
        url = self._build_url(0, -1, "/_search")
        request = self._build_request()
        resp = self._cb.post_object(url, body=request)
        result = resp.json()
        
        self._total_results = result["num_found"]
        self._count_valid = True

        return self._total_results
    
    def _perform_query(self, from_row=0, max_rows=-1):
        request = self._build_request()
        current = from_row
        numrows = 0
        still_querying = True
        while still_querying:
            url = self._build_url(from_row, max_rows, "/_search")
            resp = self._cb.post_object(url, body=request)
            result = resp.json()
            
            self._total_results = result["num_found"]
            self._count_valid = True
            
            results = result.get("results", [])
            for item in results:
                yield self._doc_class(self._cb, item["device_id"], item)
                current += 1
                numrows += 1

                if max_rows > 0 and numrows == max_rows:
                    still_querying = False
                    break

            from_row = current
            if current >= self._total_results:
                still_querying = False
                break
            
    def download(self):
        """
        Uses the query parameters that have been set to download all
        device listings in CSV format.
        
        Example::
        
        >>> cb.select(Device).status(["ALL"]).download()
        
        :return: The CSV raw data as returned from the server.
        """
        tmp = self._query_body.get("status",[])
        if tmp.is_empty():
            raise ApiError("at least one status must be specified to download")
        query_params = { "device_status": ",".join(tmp) }
        tmp = self._query_body.get("ad_group_ids", [])
        if not tmp.is_empty():
            query_params["ad_group_id"] = ",".join(tmp)
        tmp = self._query_body.get("policy_ids", [])
        if not tmp.is_empty():
            query_params["policy_id"] = ",".join(tmp)
        tmp = self._query_body.get("target_priorities", [])
        if not tmp.is_empty():
            query_params["target_priority"] = ",".join(tmp)
        tmp = self._query_builder._collapse()
        if not tmp.is_empty():
            query_params["query_string"] = tmp
        if not self._sortcriteria.is_empty():
            query_params["sort_field"] = self._sortcriteria["field_name"]
            query_params["sort_order"] = self._sortcriteria["sort_order"]
        url = self._build_url(0, -1, "/_search/download")
        return self._cb.get_raw_data(url, query_params)
