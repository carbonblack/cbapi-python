from cbapi.errors import ApiError
from cbapi.psc.base_query import QueryBuilder, PSCQueryBase
from cbapi.psc.base_query import QueryBuilderSupportMixin, IterableQueryMixin
import logging
from six import string_types

log = logging.getLogger(__name__)


class RunQuery(PSCQueryBase):
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


class RunHistoryQuery(PSCQueryBase, QueryBuilderSupportMixin, IterableQueryMixin):
    """
    Represents a query that retrieves historic LiveQuery runs.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._sort = {}

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

    def _build_request(self, start, rows):
        request = {"start": start}

        if self._query_builder:
            request["query"] = self._query_builder._collapse()
        if rows != 0:
            request["rows"] = rows
        if self._sort:
            request["sort"] = [self._sort]

        return request

    def _count(self):
        if self._count_valid:
            return self._total_results

        url = self._doc_class.urlobject_history.format(
            self._cb.credentials.org_key
        )
        request = self._build_request(start=0, rows=0)
        resp = self._cb.post_object(url, body=request)
        result = resp.json()

        self._total_results = result["num_found"]
        self._count_valid = True

        return self._total_results

    def _perform_query(self, start=0, rows=0):
        url = self._doc_class.urlobject_history.format(
            self._cb.credentials.org_key
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


class ResultQuery(PSCQueryBase, QueryBuilderSupportMixin, IterableQueryMixin):
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


class FacetQuery(PSCQueryBase, QueryBuilderSupportMixin, IterableQueryMixin):
    """
    Represents a query that receives facet information from a LiveQuery run.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._facet_fields = []
        self._criteria = {}
        self._run_id = None

    def facet_field(self, field):
        """Sets the facet fields to be received by this query.

        Example::

        >>> cb.select(ResultFacet).run_id(my_run).facet_field(["device.policy_name", "device.os"])

        :param field: Field(s) to be received, either single string or list of strings
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if isinstance(field, string_types):
            self._facet_fields.append(field)
        else:
            for name in field:
                self._facet_fields.append(name)
        return self

    def criteria(self, **kwargs):
        """Sets the filter criteria on a query's results.

        Example::

        >>> cb.select(ResultFacet).run_id(my_run).criteria(device_id=[123, 456])

        """
        self._criteria.update(kwargs)
        return self

    def run_id(self, run_id):
        """Sets the run ID to query results for.

        Example::

        >>> cb.select(ResultFacet).run_id(my_run)
        """
        self._run_id = run_id
        return self

    def _build_request(self, rows):
        terms = {"fields": self._facet_fields}
        if rows != 0:
            terms["rows"] = rows
        request = {"query": self._query_builder._collapse(), "terms": terms}
        if self._criteria:
            request["criteria"] = self._criteria
        return request

    def _perform_query(self, rows=0):
        if self._run_id is None:
            raise ApiError("Can't retrieve results without a run ID")

        url = self._doc_class.urlobject.format(
            self._cb.credentials.org_key, self._run_id
        )
        request = self._build_request(rows)
        resp = self._cb.post_object(url, body=request)
        result = resp.json()
        results = result.get("terms", [])
        for item in results:
            yield self._doc_class(self._cb, item)
