from cbapi.errors import ApiError, MoreThanOneResultError
import logging
import functools
from six import string_types
from solrq import Q

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
    valid_os = ["WINDOWS", "ANDROID", "MAC", "IOS", "LINUX", "OTHER"]
    valid_statuses = ["PENDING", "REGISTERED", "UNINSTALLED", "DEREGISTERED",
                      "ACTIVE", "INACTIVE", "ERROR", "ALL", "BYPASS_ON",
                      "BYPASS", "QUARANTINE", "SENSOR_OUTOFDATE",
                      "DELETED", "LIVE"]
    valid_priorities = ["LOW", "MEDIUM", "HIGH", "MISSION_CRITICAL"]
    valid_directions = ["ASC", "DESC"]

    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._criteria = {}
        self._time_filter = {}
        self._exclusions = {}
        self._sortcriteria = {}

    def _update_criteria(self, key, newlist):
        oldlist = self._criteria.get(key, [])
        self._criteria[key] = oldlist + newlist

    def _update_exclusions(self, key, newlist):
        oldlist = self._exclusions.get(key, [])
        self._exclusions[key] = oldlist + newlist

    def ad_group_ids(self, ad_group_ids):
        """
        Restricts the devices that this query is performed on to the specified
        AD group IDs.

        :param ad_group_ids: list of ints
        :return: This instance
        """
        if not all(isinstance(ad_group_id, int) for ad_group_id in ad_group_ids):
            raise ApiError("One or more invalid AD group IDs")
        self._update_criteria("ad_group_id", ad_group_ids)
        return self

    def device_ids(self, device_ids):
        """
        Restricts the devices that this query is performed on to the specified
        device IDs.

        :param ad_group_ids: list of ints
        :return: This instance
        """
        if not all(isinstance(device_id, int) for device_id in device_ids):
            raise ApiError("One or more invalid device IDs")
        self._update_criteria("id", device_ids)
        return self

    def last_contact_time(self, *args, **kwargs):
        """
        Restricts the devices that this query is performed on to the specified
        last contact time (either specified as a start and end point or as a
        range).

        :return: This instance
        """
        if kwargs.get("start", None) and kwargs.get("end", None):
            if kwargs.get("range", None):
                raise ApiError("cannot specify range= in addition to start= and end=")
            stime = kwargs["start"]
            if not isinstance(stime, str):
                stime = stime.isoformat()
            etime = kwargs["end"]
            if not isinstance(etime, str):
                etime = etime.isoformat()
            self._time_filter = {"start": stime, "end": etime}
        elif kwargs.get("range", None):
            if kwargs.get("start", None) or kwargs.get("end", None):
                raise ApiError("cannot specify start= or end= in addition to range=")
            self._time_filter = {"range": kwargs["range"]}
        else:
            raise ApiError("must specify either start= and end= or range=")
        return self

    def os(self, operating_systems):
        """
        Restricts the devices that this query is performed on to the specified
        operating systems.

        :param operating_systems: list of operating systems
        :return: This instance
        """
        if not all((osval in DeviceSearchQuery.valid_os) for osval in operating_systems):
            raise ApiError("One or more invalid operating systems")
        self._update_criteria("os", operating_systems)
        return self

    def policy_ids(self, policy_ids):
        """
        Restricts the devices that this query is performed on to the specified
        policy IDs.

        :param policy_ids: list of ints
        :return: This instance
        """
        if not all(isinstance(policy_id, int) for policy_id in policy_ids):
            raise ApiError("One or more invalid policy IDs")
        self._update_criteria("policy_id", policy_ids)
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
        self._update_criteria("status", statuses)
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
        self._update_criteria("target_priority", target_priorities)
        return self

    def exclude_sensor_versions(self, sensor_versions):
        """
        Restricts the devices that this query is performed on to exclude specified
        sensor versions.

        :param sensor_versions: List of sensor versions to exclude
        :return: This instance
        """
        if not all(isinstance(v, str) for v in sensor_versions):
            raise ApiError("One or more invalid sensor versions")
        self._update_exclusions("sensor_version", sensor_versions)
        return self

    def sort_by(self, key, direction="ASC"):
        """Sets the sorting behavior on a query's results.

        Example::

        >>> cb.select(Device).sort_by("name")

        :param key: the key in the schema to sort by
        :param direction: the sort order, either "ASC" or "DESC"
        :rtype: :py:class:`DeviceSearchQuery`
        """
        if direction not in DeviceSearchQuery.valid_directions:
            raise ApiError("invalid sort direction specified")
        self._sortcriteria = {"field": key, "order": direction}
        return self

    def _build_request(self, from_row, max_rows):
        mycrit = self._criteria
        if self._time_filter:
            mycrit["last_contact_time"] = self._time_filter
        request = {"criteria": mycrit, "exclusions": self._exclusions}
        request["query"] = self._query_builder._collapse()
        if from_row > 0:
            request["start"] = from_row
        if max_rows >= 0:
            request["rows"] = max_rows
        if self._sortcriteria != {}:
            request["sort"] = [self._sortcriteria]
        return request

    def _build_url(self, tail_end):
        url = self._doc_class.urlobject.format(
            self._cb.credentials.org_key) + tail_end
        return url

    def _count(self):
        if self._count_valid:
            return self._total_results

        url = self._build_url("/_search")
        request = self._build_request(0, -1)
        resp = self._cb.post_object(url, body=request)
        result = resp.json()

        self._total_results = result["num_found"]
        self._count_valid = True

        return self._total_results

    def _perform_query(self, from_row=0, max_rows=-1):
        url = self._build_url("/_search")
        current = from_row
        numrows = 0
        still_querying = True
        while still_querying:
            request = self._build_request(current, max_rows)
            resp = self._cb.post_object(url, body=request)
            result = resp.json()

            self._total_results = result["num_found"]
            self._count_valid = True

            results = result.get("results", [])
            for item in results:
                yield self._doc_class(self._cb, item["id"], item)
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
        tmp = self._criteria.get("status", [])
        if not tmp:
            raise ApiError("at least one status must be specified to download")
        query_params = {"status": ",".join(tmp)}
        tmp = self._criteria.get("ad_group_id", [])
        if tmp:
            query_params["ad_group_id"] = ",".join([str(t) for t in tmp])
        tmp = self._criteria.get("policy_id", [])
        if tmp:
            query_params["policy_id"] = ",".join([str(t) for t in tmp])
        tmp = self._criteria.get("target_priority", [])
        if tmp:
            query_params["target_priority"] = ",".join(tmp)
        tmp = self._query_builder._collapse()
        if tmp:
            query_params["query_string"] = tmp
        if self._sortcriteria:
            query_params["sort_field"] = self._sortcriteria["field"]
            query_params["sort_order"] = self._sortcriteria["order"]
        url = self._build_url("/_search/download")
        # AGRB 10/3/2019 - Header is TEMPORARY until bug is fixed in API. Remove when fix deployed.
        return self._cb.get_raw_data(url, query_params, headers={"Content-Type": "application/json"})

    def _bulk_device_action(self, action_type, options=None):
        request = {"action_type": action_type, "search": self._build_request(0, -1)}
        if options:
            request["options"] = options
        return self._cb._raw_device_action(request)

    def background_scan(self, flag):
        """
        Set the background scan option for the specified devices.

        :param boolean flag: True to turn background scan on, False to turn it off.
        """
        return self._bulk_device_action("BACKGROUND_SCAN", self._cb._action_toggle(flag))

    def bypass(self, flag):
        """
        Set the bypass option for the specified devices.

        :param boolean flag: True to enable bypass, False to disable it.
        """
        return self._bulk_device_action("BYPASS", self._cb._action_toggle(flag))

    def delete_sensor(self):
        """
        Delete the specified sensor devices.
        """
        return self._bulk_device_action("DELETE_SENSOR")

    def uninstall_sensor(self):
        """
        Uninstall the specified sensor devices.
        """
        return self._bulk_device_action("UNINSTALL_SENSOR")

    def quarantine(self, flag):
        """
        Set the quarantine option for the specified devices.

        :param boolean flag: True to enable quarantine, False to disable it.
        """
        return self._bulk_device_action("QUARANTINE", self._cb._action_toggle(flag))

    def update_policy(self, policy_id):
        """
        Set the current policy for the specified devices.

        :param int policy_id: ID of the policy to set for the devices.
        """
        return self._bulk_device_action("UPDATE_POLICY", {"policy_id": policy_id})

    def update_sensor_version(self, sensor_version):
        """
        Update the sensor version for the specified devices.

        :param dict sensor_version: New version properties for the sensor.
        """
        return self._bulk_device_action("UPDATE_SENSOR_VERSION",
                                        {"sensor_version": sensor_version})
        

class AlertRequestCriteriaBuilder:
    """
    Auxiliary object that builds the criteria for alert request searches.
    """
    valid_categories = ["THREAT", "MONITORED", "INFO", "MINOR", "SERIOUS", "CRITICAL"]
    valid_reputations = ["KNOWN_MALWARE", "SUSPECT_MALWARE", "PUP", "NOT_LISTED", "ADAPTIVE_WHITE_LIST",
                         "COMMON_WHITE_LIST", "TRUSTED_WHITE_LIST", "COMPANY_BLACK_LIST"]
    valid_alerttypes = ["CB_ANALYTICS", "VMWARE", "WATCHLIST"]
    valid_workflow_vals = ["OPEN", "DISMISSED"]
     
    def __init__(self):
        self._criteria = {}
        self._time_filter = {}
        
    def _update_criteria(self, key, newlist):
        oldlist = self._criteria.get(key, [])
        self._criteria[key] = oldlist + newlist
        
    def categories(self, cats):
        """
        Restricts the alerts that this query is performed on to the specified categories.
        
        :param cats list: List of categories to be restricted to. Valid categories are
                          "THREAT", "MONITORED", "INFO", "MINOR", "SERIOUS", and "CRITICAL."
        :return: This instance
        """
        if not all((c in AlertRequestCriteriaBuilder.valid_categories) for c in cats):
            raise ApiError("One or more invalid category values")
        self._update_criteria("category", cats)
        return self
        
    def create_time(self, *args, **kwargs):
        """
        Restricts the alerts that this query is performed on to the specified
        creation time (either specified as a start and end point or as a
        range).

        :return: This instance
        """
        if kwargs.get("start", None) and kwargs.get("end", None):
            if kwargs.get("range", None):
                raise ApiError("cannot specify range= in addition to start= and end=")
            stime = kwargs["start"]
            if not isinstance(stime, str):
                stime = stime.isoformat()
            etime = kwargs["end"]
            if not isinstance(etime, str):
                etime = etime.isoformat()
            self._time_filter = {"start": stime, "end": etime}
        elif kwargs.get("range", None):
            if kwargs.get("start", None) or kwargs.get("end", None):
                raise ApiError("cannot specify start= or end= in addition to range=")
            self._time_filter = {"range": kwargs["range"]}
        else:
            raise ApiError("must specify either start= and end= or range=")
        return self

    def device_ids(self, device_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        device IDs.

        :param device_ids list: list of integer device IDs
        :return: This instance
        """
        if not all(isinstance(device_id, int) for device_id in device_ids):
            raise ApiError("One or more invalid device IDs")
        self._update_criteria("device_id", device_ids)
        return self

    def device_names(self, device_names):
        """
        Restricts the alerts that this query is performed on to the specified
        device names.

        :param device_names list: list of string device names
        :return: This instance
        """
        if not all(isinstance(n, str) for n in device_names):
            raise ApiError("One or more invalid device names")
        self._update_criteria("device_name", device_names)
        return self
        
    def device_os(self, device_os): 
        """
        Restricts the alerts that this query is performed on to the specified
        device operating systems.

        :param device_os list: List of string operating systems.  Valid values are
                               "WINDOWS", "ANDROID", "MAC", "IOS", "LINUX", and "OTHER."
        :return: This instance
        """
        if not all((osval in DeviceSearchQuery.valid_os) for osval in device_os):
            raise ApiError("One or more invalid operating systems")
        self._update_criteria("device_os", device_os)
        return self
    
    def device_os_version(self, device_os_versions):
        """
        Restricts the alerts that this query is performed on to the specified
        device operating system versions.

        :param device_os_versions list: List of string operating system versions.
        :return: This instance
        """
        if not all(isinstance(n, str) for n in device_os_versions):
            raise ApiError("One or more invalid device OS versions")
        self._update_criteria("device_os_version", device_os_versions)
        return self
    
    def device_username(self, users):
        """
        Restricts the alerts that this query is performed on to the specified
        user names.

        :param users list: List of string user names.
        :return: This instance
        """
        if not all(isinstance(u, str) for u in users):
            raise ApiError("One or more invalid user names")
        self._update_criteria("device_username", users)
        return self
    
    def group_results(self, flag):
        """
        Specifies whether or not to group the results of the query.
        
        :param flag boolean: True to group the results, False to not do so.
        :return: This instance
        """
        self._criteria["group_results"] = True if flag else False
        return self
    
    def alert_ids(self, alert_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        alert IDs.

        :param alert_ids list: List of string alert IDs.
        :return: This instance
        """
        if not all(isinstance(v, str) for v in alert_ids):
            raise ApiError("One or more invalid alert ID values")
        self._update_criteria("id", alert_ids)
        return self
    
    def legacy_alert_ids(self, alert_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        legacy alert IDs.

        :param alert_ids list: List of string legacy alert IDs.
        :return: This instance
        """
        if not all(isinstance(v, str) for v in alert_ids):
            raise ApiError("One or more invalid alert ID values")
        self._update_criteria("legacy_alert_id", alert_ids)
        return self
    
    def minimum_severity(self, severity):
        """
        Restricts the alerts that this query is performed on to the specified
        minimum severity level.
        
        :param severity int: The minimum severity level for alerts.
        :return: This instance
        """
        self._criteria["minimum_severity"] = severity
        return self
    
    def policy_ids(self, policy_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        policy IDs.

        :param policy_ids list: list of integer policy IDs
        :return: This instance
        """
        if not all(isinstance(policy_id, int) for policy_id in policy_ids):
            raise ApiError("One or more invalid policy IDs")
        self._update_criteria("policy_id", policy_ids)
        return self

    def policy_names(self, policy_names):
        """
        Restricts the alerts that this query is performed on to the specified
        policy names.

        :param policy_names list: list of string policy names
        :return: This instance
        """
        if not all(isinstance(n, str) for n in policy_names):
            raise ApiError("One or more invalid policy names")
        self._update_criteria("policy_name", policy_names)
        return self
    
    def process_names(self, process_names):
        """
        Restricts the alerts that this query is performed on to the specified
        process names.

        :param process_names list: list of string process names
        :return: This instance
        """
        if not all(isinstance(n, str) for n in process_names):
            raise ApiError("One or more invalid process names")
        self._update_criteria("process_name", process_names)
        return self
    
    def process_sha256(self, shas):
        """
        Restricts the alerts that this query is performed on to the specified
        process SHA-256 hash values.

        :param shas list: list of string process SHA-256 hash values
        :return: This instance
        """
        if not all(isinstance(n, str) for n in shas):
            raise ApiError("One or more invalid SHA256 values")
        self._update_criteria("process_sha256", shas)
        return self
        
    def reputations(self, reps):
        """
        Restricts the alerts that this query is performed on to the specified
        reputation values.

        :param reps list: List of string reputation values.  Valid values are
                          "KNOWN_MALWARE", "SUSPECT_MALWARE", "PUP", "NOT_LISTED",
                          "ADAPTIVE_WHITE_LIST", "COMMON_WHITE_LIST",
                          "TRUSTED_WHITE_LIST", and "COMPANY_BLACK_LIST".
        :return: This instance
        """
        if not all((r in AlertRequestCriteriaBuilder.valid_reputations) for r in reps):
            raise ApiError("One or more invalid reputation values")
        self._update_criteria("reputation", reps)
        return self
    
    def tags(self, tags):
        """
        Restricts the alerts that this query is performed on to the specified
        tag values.

        :param tags list: list of string tag values
        :return: This instance
        """
        if not all(isinstance(tag, str) for tag in tags):
            raise ApiError("One or more invalid tags")
        self._update_criteria("tag", tags)
        return self
        
    def target_priorities(self, priorities):
        """
        Restricts the alerts that this query is performed on to the specified
        target priority values.

        :param priorities list: List of string target priority values.  Valid values are
                                "LOW", "MEDIUM", "HIGH", and "MISSION_CRITICAL".
        :return: This instance
        """
        if not all((prio in DeviceSearchQuery.valid_priorities) for prio in priorities):
            raise ApiError("One or more invalid priority values")
        self._update_criteria("target_value", priorities)
        return self
        
    def threat_ids(self, threats):
        """
        Restricts the alerts that this query is performed on to the specified
        threat ID values.

        :param threats list: list of string threat ID values
        :return: This instance
        """
        if not all(isinstance(t, str) for t in threats):
            raise ApiError("One or more invalid threat ID values")
        self._update_criteria("threat_id", threats)
        return self
    
    def types(self, alerttypes):
        """
        Restricts the alerts that this query is performed on to the specified
        alert type values.

        :param alerttypes list: List of string alert type values.  Valid values are
                                "CB_ANALYTICS", "VMWARE", and "WATCHLIST".
        :return: This instance
        """
        if not all((t in AlertRequestCriteriaBuilder.valid_alerttypes) for t in alerttypes):
            raise ApiError("One or more invalid alert type values")
        self._update_criteria("type", alerttypes)
        return self
    
    def workflows(self, workflow_vals):
        """
        Restricts the alerts that this query is performed on to the specified
        workflow status values.

        :param workflow_vals list: List of string alert type values.  Valid values are
                                   "OPEN" and "DISMISSED".
        :return: This instance
        """
        if not all((t in AlertRequestCriteriaBuilder.valid_workflow_vals) for t in workflow_vals):
            raise ApiError("One or more invalid workflow status values")
        self._update_criteria("workflow", workflow_vals)
        return self
    
    def build(self):
        """
        Builds the criteria object for use in a query.
        
        :return: The criteria object.
        """
        mycrit = self._criteria
        if self._time_filter:
            mycrit["create_time"] = self._time_filter
        return mycrit
    
    
class CBAnalyticsAlertRequestCriteriaBuilder(AlertRequestCriteriaBuilder):     
    """
    Auxiliary object that builds the criteria for CB Analytics alert request searches.
    """
    valid_threat_categories = ["UNKNOWN", "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", "RISKY_PROGRAM"]
    valid_locations = ["ONSITE", "OFFSITE", "UNKNOWN"]
    valid_kill_chain_statuses = ["RECONNAISSANCE", "WEAPONIZE", "DELIVER_EXPLOIT", "INSTALL_RUN",
                                 "COMMAND_AND_CONTROL", "EXECUTE_GOAL", "BREACH"]
    valid_policy_applied = ["APPLIED", "NOT_APPLIED"]
    valid_run_states = ["DID_NOT_RUN", "RAN", "UNKNOWN"]
    valid_sensor_actions = ["POLICY_NOT_APPLIED", "ALLOW", "ALLOW_AND_LOG", "TERMINATE", "DENY"]
    valid_threat_cause_vectors = ["EMAIL", "WEB", "GENERIC_SERVER", "GENERIC_CLIENT", "REMOTE_DRIVE",
                                  "REMOVABLE_MEDIA", "UNKNOWN", "APP_STORE", "THIRD_PARTY"]
    def __init__(self):
        super().__init__()
        
    def blocked_threat_categories(self, categories):
        """
        Restricts the alerts that this query is performed on to the specified
        threat categories that were blocked.
        
        :param categories list: List of threat categories to look for.  Valid values are "UNKNOWN",
                                "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", and "RISKY_PROGRAM".
        :return: This instance.
        """
        if not all((category in CBAnalyticsAlertRequestCriteriaBuilder.valid_threat_categories) \
                   for category in categories):
            raise ApiError("One or more invalid threat categories")
        self._update_criteria("blocked_threat_category", categories)
        return self
    
    def device_locations(self, locations):
        """
        Restricts the alerts that this query is performed on to the specified
        device locations.
        
        :param locations list: List of device locations to look for. Valid values are "ONSITE", "OFFSITE",
                               and "UNKNOWN". 
        :return: This instance.
        """
        if not all((location in CBAnalyticsAlertRequestCriteriaBuilder.valid_locations) \
                   for location in locations):
            raise ApiError("One or more invalid device locations")
        self._update_criteria("device_location", locations)
        return self
        
    def kill_chain_statuses(self, statuses):
        """
        Restricts the alerts that this query is performed on to the specified
        kill chain statuses.
        
        :param statuses list: List of kill chain statuses to look for. Valid values are "RECONNAISSANCE",
                              "WEAPONIZE", "DELIVER_EXPLOIT", "INSTALL_RUN","COMMAND_AND_CONTROL",
                              "EXECUTE_GOAL", and "BREACH". 
        :return: This instance.
        """
        if not all((status in CBAnalyticsAlertRequestCriteriaBuilder.valid_threat_categories) \
                   for status in statuses):
            raise ApiError("One or more invalid kill chain status values")
        self._update_criteria("kill_chain_status", statuses)
        return self
    
    def not_blocked_threat_categories(self, categories):
        """
        Restricts the alerts that this query is performed on to the specified
        threat categories that were NOT blocked.
        
        :param categories list: List of threat categories to look for.  Valid values are "UNKNOWN",
                                "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", and "RISKY_PROGRAM".
        :return: This instance.
        """
        if not all((category in CBAnalyticsAlertRequestCriteriaBuilder.valid_threat_categories) \
                   for category in categories):
            raise ApiError("One or more invalid threat categories")
        self._update_criteria("not_blocked_threat_category", categories)
        return self
    
    def policy_applied(self, applied_statuses):
        """
        Restricts the alerts that this query is performed on to the specified
        status values showing whether policies were applied.
        
        :param applied_statuses list: List of status values to look for. Valid values are
                                      "APPLIED" and "NOT_APPLIED". 
        :return: This instance.
        """
        if not all((s in CBAnalyticsAlertRequestCriteriaBuilder.valid_policy_applied) \
                   for s in applied_statuses):
            raise ApiError("One or more invalid policy-applied values")
        self._update_criteria("policy_applied", applied_statuses)
        return self
    
    def reason_code(self, reason):
        """
        Restricts the alerts that this query is performed on to the specified
        reason code (enum value).
        
        :param reason str: The reason code to look for.
        :return: This instance.
        """
        self._criteria["reason_code"] = reason
        return self
    
    def run_states(self, states):
        """
        Restricts the alerts that this query is performed on to the specified run states.
        
        :param states list: List of run states to look for. Valid values are "DID_NOT_RUN", "RAN",
                            and "UNKNOWN". 
        :return: This instance.
        """
        if not all((s in CBAnalyticsAlertRequestCriteriaBuilder.valid_run_states) \
                   for s in states):
            raise ApiError("One or more invalid run states")
        self._update_criteria("run_state", states)
        return self
    
    def sensor_actions(self, actions):
        """
        Restricts the alerts that this query is performed on to the specified sensor actions.
        
        :param actions list: List of sensor actions to look for. Valid values are "POLICY_NOT_APPLIED",
                             "ALLOW", "ALLOW_AND_LOG", "TERMINATE", and "DENY".
        :return: This instance.
        """
        if not all((action in CBAnalyticsAlertRequestCriteriaBuilder.valid_sensor_actions) \
                   for action in actions):
            raise ApiError("One or more invalid sensor actions")
        self._update_criteria("sensor_action", actions)
        return self
    
    def threat_cause_vectors(self, vectors):
        """
        Restricts the alerts that this query is performed on to the specified threat cause vectors.
        
        :param vectors list: List of threat cause vectors to look for.  Valid values are "EMAIL", "WEB",
                             "GENERIC_SERVER", "GENERIC_CLIENT", "REMOTE_DRIVE", "REMOVABLE_MEDIA",
                             "UNKNOWN", "APP_STORE", and "THIRD_PARTY".
        :return: This instance.
        """
        if not all((vector in CBAnalyticsAlertRequestCriteriaBuilder.valid_threat_cause_vectors) \
                   for vector in vectors):
            raise ApiError("One or more invalid threat cause vectors")
        self._update_criteria("threat_cause_vector", vectors)
        return self
    
    
class VMwareAlertRequestCriteriaBuilder(AlertRequestCriteriaBuilder):    
    """
    Auxiliary object that builds the criteria for VMware alert request searches.
    """
    def __init__(self):
        super().__init__()
        
    def group_ids(self, groupids):
        """
        Restricts the alerts that this query is performed on to the specified
        AppDefense-assigned alarm group IDs.
        
        :param groupids list: List of (integer) AppDefense-assigned alarm group IDs.
        :return: This instance.
        """
        if not all(isinstance(groupid, int) for groupid in groupids):
            raise ApiError("One or more invalid alarm group IDs")
        self._update_criteria("group_id", groupids)
        return self
    
    
class WatchlistAlertRequestCriteriaBuilder(AlertRequestCriteriaBuilder):
    """
    Auxiliary object that builds the criteria for watchlist alert request searches.
    """
    def __init__(self):
        super().__init__()
        
    def watchlist_ids(self, ids):
        """
        Restricts the alerts that this query is performed on to the specified
        watchlist ID values.

        :param ids list: list of string watchlist ID values
        :return: This instance
        """
        if not all(isinstance(t, str) for t in ids):
            raise ApiError("One or more invalid watchlist IDs")
        self._update_criteria("watchlist_id", ids)
        return self
        
    def watchlist_names(self, names):
        """
        Restricts the alerts that this query is performed on to the specified
        watchlist name values.

        :param names list: list of string watchlist name values
        :return: This instance
        """
        if not all(isinstance(name, str) for name in names):
            raise ApiError("One or more invalid watchlist names")
        self._update_criteria("watchlist_name", names)
        return self


class AlertCriteriaBuilderMixin:
    """
    Added to query classes to allow them to manipulate alert criteria for queries.
    """
    def categories(self, cats):
        """
        Restricts the alerts that this query is performed on to the specified categories.
        
        :param cats list: List of categories to be restricted to. Valid categories are
                          "THREAT", "MONITORED", "INFO", "MINOR", "SERIOUS", and "CRITICAL."
        :return: This instance
        """
        self._criteria_builder.categories(cats)
        return self
        
    def create_time(self, *args, **kwargs):
        """
        Restricts the alerts that this query is performed on to the specified
        creation time (either specified as a start and end point or as a
        range).

        :return: This instance
        """
        self._criteria_builder.create_time(*args, **kwargs)
        return self

    def device_ids(self, device_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        device IDs.

        :param device_ids list: list of integer device IDs
        :return: This instance
        """
        self._criteria_builder.device_ids(device_ids)
        return self

    def device_names(self, device_names):
        """
        Restricts the alerts that this query is performed on to the specified
        device names.

        :param device_names list: list of string device names
        :return: This instance
        """
        self._criteria_builder.device_names(device_names)
        return self
        
    def device_os(self, device_os): 
        """
        Restricts the alerts that this query is performed on to the specified
        device operating systems.

        :param device_os list: List of string operating systems.  Valid values are
                               "WINDOWS", "ANDROID", "MAC", "IOS", "LINUX", and "OTHER."
        :return: This instance
        """
        self._criteria_builder.device_os(device_os)
        return self
    
    def device_os_version(self, device_os_versions):
        """
        Restricts the alerts that this query is performed on to the specified
        device operating system versions.

        :param device_os_versions list: List of string operating system versions.
        :return: This instance
        """
        self._criteria_builder.device_os_versions(device_os_versions)
        return self
    
    def device_username(self, users):
        """
        Restricts the alerts that this query is performed on to the specified
        user names.

        :param users list: List of string user names.
        :return: This instance
        """
        self._criteria_builder.device_username(users)
        return self
    
    def group_results(self, flag):
        """
        Specifies whether or not to group the results of the query.
        
        :param flag boolean: True to group the results, False to not do so.
        :return: This instance
        """
        self._criteria_builder.group_results(flag)
        return self
    
    def alert_ids(self, alert_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        alert IDs.

        :param alert_ids list: List of string alert IDs.
        :return: This instance
        """
        self._criteria_builder.alert_ids(alert_ids)
        return self
    
    def legacy_alert_ids(self, alert_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        legacy alert IDs.

        :param alert_ids list: List of string legacy alert IDs.
        :return: This instance
        """
        self._criteria_builder.legacy_alert_ids(alert_ids)
        return self
    
    def minimum_severity(self, severity):
        """
        Restricts the alerts that this query is performed on to the specified
        minimum severity level.
        
        :param severity int: The minimum severity level for alerts.
        :return: This instance
        """
        self._criteria_builder.minimum_severity(severity)
        return self
    
    def policy_ids(self, policy_ids):
        """
        Restricts the alerts that this query is performed on to the specified
        policy IDs.

        :param policy_ids list: list of integer policy IDs
        :return: This instance
        """
        self._criteria_builder.policy_ids(policy_ids)
        return self

    def policy_names(self, policy_names):
        """
        Restricts the alerts that this query is performed on to the specified
        policy names.

        :param policy_names list: list of string policy names
        :return: This instance
        """
        self._criteria_builder.policy_names(policy_names)
        return self
    
    def process_names(self, process_names):
        """
        Restricts the alerts that this query is performed on to the specified
        process names.

        :param process_names list: list of string process names
        :return: This instance
        """
        self._criteria_builder.process_names(process_names)
        return self
    
    def process_sha256(self, shas):
        """
        Restricts the alerts that this query is performed on to the specified
        process SHA-256 hash values.

        :param shas list: list of string process SHA-256 hash values
        :return: This instance
        """
        self._criteria_builder.process_sha256(shas)
        return self
        
    def reputations(self, reps):
        """
        Restricts the alerts that this query is performed on to the specified
        reputation values.

        :param reps list: List of string reputation values.  Valid values are
                          "KNOWN_MALWARE", "SUSPECT_MALWARE", "PUP", "NOT_LISTED",
                          "ADAPTIVE_WHITE_LIST", "COMMON_WHITE_LIST",
                          "TRUSTED_WHITE_LIST", and "COMPANY_BLACK_LIST".
        :return: This instance
        """
        self._criteria_builder.reputations(reps)
        return self
    
    def tags(self, tags):
        """
        Restricts the alerts that this query is performed on to the specified
        tag values.

        :param tags list: list of string tag values
        :return: This instance
        """
        self._criteria_builder.tags(tags)
        return self
        
    def target_priorities(self, priorities):
        """
        Restricts the alerts that this query is performed on to the specified
        target priority values.

        :param reps list: List of string target priority values.  Valid values are
                          "LOW", "MEDIUM", "HIGH", and "MISSION_CRITICAL".
        :return: This instance
        """
        self._criteria_builder.target_priorities(priorities)
        return self
        
    def threat_ids(self, threats):
        """
        Restricts the alerts that this query is performed on to the specified
        threat ID values.

        :param threats list: list of string threat ID values
        :return: This instance
        """
        self._criteria_builder.threat_ids(threats)
        return self
    
    def types(self, alerttypes):
        """
        Restricts the alerts that this query is performed on to the specified
        alert type values.

        :param alerttypes list: List of string alert type values.  Valid values are
                                "CB_ANALYTICS", "VMWARE", and "WATCHLIST".
        :return: This instance
        """
        self._criteria_builder.types(alerttypes)
        return self
    
    def workflows(self, workflow_vals):
        """
        Restricts the alerts that this query is performed on to the specified
        workflow status values.

        :param workflow_vals list: List of string alert type values.  Valid values are
                                   "OPEN" and "DISMISSED".
        :return: This instance
        """
        self._criteria_builder.workflows(workflow_vals)
        return self


class CBAnalyticsAlertCriteriaBuilderMixin(AlertCriteriaBuilderMixin):
    """
    Added to query classes to allow them to manipulate CB Analytics alert criteria for queries.
    """
    def blocked_threat_categories(self, categories):
        """
        Restricts the alerts that this query is performed on to the specified
        threat categories that were blocked.
        
        :param categories list: List of threat categories to look for.  Valid values are "UNKNOWN",
                                "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", and "RISKY_PROGRAM".
        :return: This instance.
        """
        self._criteria_builder.blocked_threat_categories(categories)
        return self
    
    def device_locations(self, locations):
        """
        Restricts the alerts that this query is performed on to the specified
        device locations.
        
        :param locations list: List of device locations to look for. Valid values are "ONSITE", "OFFSITE",
                               and "UNKNOWN". 
        :return: This instance.
        """
        self._criteria_builder.device_locations(locations)
        return self
        
    def kill_chain_statuses(self, statuses):
        """
        Restricts the alerts that this query is performed on to the specified
        kill chain statuses.
        
        :param statuses list: List of kill chain statuses to look for. Valid values are "RECONNAISSANCE",
                              "WEAPONIZE", "DELIVER_EXPLOIT", "INSTALL_RUN","COMMAND_AND_CONTROL",
                              "EXECUTE_GOAL", and "BREACH". 
        :return: This instance.
        """
        self._criteria_builder.kill_chain_statuses(statuses)
        return self
    
    def not_blocked_threat_categories(self, categories):
        """
        Restricts the alerts that this query is performed on to the specified
        threat categories that were NOT blocked.
        
        :param categories list: List of threat categories to look for.  Valid values are "UNKNOWN",
                                "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", and "RISKY_PROGRAM".
        :return: This instance.
        """
        self._criteria_builder.not_blocked_threat_categories(categories)
        return self
    
    def policy_applied(self, applied_statuses):
        """
        Restricts the alerts that this query is performed on to the specified
        status values showing whether policies were applied.
        
        :param applied_statuses list: List of status values to look for. Valid values are
                                      "APPLIED" and "NOT_APPLIED". 
        :return: This instance.
        """
        self._criteria_builder.policy_applied(applied_statuses)
        return self
    
    def reason_code(self, reason):
        """
        Restricts the alerts that this query is performed on to the specified
        reason code (enum value).
        
        :param reason str: The reason code to look for.
        :return: This instance.
        """
        self._criteria_builder.reason_code(reason)
        return self
    
    def run_states(self, states):
        """
        Restricts the alerts that this query is performed on to the specified run states.
        
        :param states list: List of run states to look for. Valid values are "DID_NOT_RUN", "RAN",
                            and "UNKNOWN". 
        :return: This instance.
        """
        self._criteria_builder.run_states(states)
        return self
    
    def sensor_actions(self, actions):
        """
        Restricts the alerts that this query is performed on to the specified sensor actions.
        
        :param actions list: List of sensor actions to look for. Valid values are "POLICY_NOT_APPLIED",
                             "ALLOW", "ALLOW_AND_LOG", "TERMINATE", and "DENY".
        :return: This instance.
        """
        self._criteria_builder.sensor_actions(actions)
        return self
    
    def threat_cause_vectors(self, vectors):
        """
        Restricts the alerts that this query is performed on to the specified threat cause vectors.
        
        :param vectors list: List of threat cause vectors to look for.  Valid values are "EMAIL", "WEB",
                             "GENERIC_SERVER", "GENERIC_CLIENT", "REMOTE_DRIVE", "REMOVABLE_MEDIA",
                             "UNKNOWN", "APP_STORE", and "THIRD_PARTY".
        :return: This instance.
        """
        self._criteria_builder.threat_cause_vectors(vectors)
        return self
    

class VMwareAlertCriteriaBuilderMixin(AlertCriteriaBuilderMixin):
    """
    Added to query classes to allow them to manipulate VMware alert criteria for queries.
    """
    def group_ids(self, groupids):
        """
        Restricts the alerts that this query is performed on to the specified
        AppDefense-assigned alarm group IDs.
        
        :param groupids list: List of (integer) AppDefense-assigned alarm group IDs.
        :return: This instance.
        """
        self._criteria_builder.group_ids(groupids)
        return self


class WatchlistAlertCriteriaBuilderMixin(AlertCriteriaBuilderMixin):
    """
    Added to query classes to allow them to manipulate watchlist alert criteria for queries.
    """
    def watchlist_ids(self, ids):
        """
        Restricts the alerts that this query is performed on to the specified
        watchlist ID values.

        :param ids list: list of string watchlist ID values
        :return: This instance
        """
        self._criteria_builder.watchlist_ids(ids)
        return self
        
    def watchlist_names(self, names):
        """
        Restricts the alerts that this query is performed on to the specified
        watchlist name values.

        :param names list: list of string watchlist name values
        :return: This instance
        """
        self._criteria_builder.watchlist_names(names)
        return self
    
    
class BaseAlertSearchQuery(PSCQueryBase, QueryBuilderSupportMixin, AlertCriteriaBuilderMixin,
                           IterableQueryMixin):
    """
    Represents a query that is used to locate BaseAlert objects.
    """
    valid_facet_fields = ["ALERT_TYPE", "CATEGORY", "REPUTATION", "WORKFLOW", "TAG", "POLICY_ID",
                          "POLICY_NAME", "DEVICE_ID", "DEVICE_NAME", "APPLICATION_HASH",
                          "APPLICATION_NAME", "STATUS", "RUN_STATE", "POLICY_APPLIED_STATE",
                          "POLICY_APPLIED", "SENSOR_ACTION"]
    
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._criteria_builder = AlertRequestCriteriaBuilder()
        self._sortcriteria = {}
        
    def sort_by(self, key, direction="ASC"):
        """Sets the sorting behavior on a query's results.

        Example::

        >>> cb.select(BaseAlert).sort_by("name")

        :param key: the key in the schema to sort by
        :param direction: the sort order, either "ASC" or "DESC"
        :rtype: :py:class:`BaseAlertSearchQuery`
        """
        if direction not in DeviceSearchQuery.valid_directions:
            raise ApiError("invalid sort direction specified")
        self._sortcriteria = {"field": key, "order": direction}
        return self

    def _build_request(self, from_row, max_rows, add_sort=True):
        request = {"criteria": self._criteria_builder.build()}   
        request["query"] = self._query_builder._collapse()
        if from_row > 0:
            request["start"] = from_row
        if max_rows >= 0:
            request["rows"] = max_rows
        if add_sort and self._sortcriteria != {}:
            request["sort"] = [self._sortcriteria]
        return request
        
    def _build_url(self, tail_end):
        url = self._doc_class.urlobject.format(self._cb.credentials.org_key) + tail_end
        return url

    def _count(self):
        if self._count_valid:
            return self._total_results

        url = self._build_url("/_search")
        request = self._build_request(0, -1)
        resp = self._cb.post_object(url, body=request)
        result = resp.json()

        self._total_results = result["num_found"]
        self._count_valid = True

        return self._total_results

    def _perform_query(self, from_row=0, max_rows=-1):
        url = self._build_url("/_search")
        current = from_row
        numrows = 0
        still_querying = True
        while still_querying:
            request = self._build_request(current, max_rows)
            resp = self._cb.post_object(url, body=request)
            result = resp.json()

            self._total_results = result["num_found"]
            self._count_valid = True

            results = result.get("results", [])
            for item in results:
                yield self._doc_class(self._cb, item["id"], item)
                current += 1
                numrows += 1

                if max_rows > 0 and numrows == max_rows:
                    still_querying = False
                    break

            from_row = current
            if current >= self._total_results:
                still_querying = False
                break

    def facets(self, fieldlist, max_rows=0):
        """
        Return information about the facets for this alert by search, using the defined criteria.
        
        :param fieldlist list: List of facet field names. Valid names are
                               "ALERT_TYPE", "CATEGORY", "REPUTATION", "WORKFLOW", "TAG", "POLICY_ID",
                               "POLICY_NAME", "DEVICE_ID", "DEVICE_NAME", "APPLICATION_HASH",
                               "APPLICATION_NAME", "STATUS", "RUN_STATE", "POLICY_APPLIED_STATE",
                               "POLICY_APPLIED", and "SENSOR_ACTION".
        :param max_rows int: The maximum number of rows to return. 0 means return all rows.
        :return: A list of facet information specified as dicts.
        """
        if not all((field in BaseAlertSearchQuery.valid_facet_fields) for field in fieldlist):
            raise ApiError("One or more invalid term field names")
        request = self._build_request(0, -1, False)
        request["terms"] = {"fields": fieldlist, "rows": max_rows}
        url = self._build_url("/_facet")
        resp = self._cb.post_object(url, body=request)
        result = resp.json()
        return result.get("results", [])
            
            
class WatchlistAlertSearchQuery(BaseAlertSearchQuery, WatchlistAlertCriteriaBuilderMixin):
    """
    Represents a query that is used to locate WatchlistAlert objects.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._criteria_builder = WatchlistAlertRequestCriteriaBuilder()
        
        
class CBAnalyticsAlertSearchQuery(BaseAlertSearchQuery, CBAnalyticsAlertCriteriaBuilderMixin):
    """
    Represents a query that is used to locate CBAnalyticsAlert objects.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._criteria_builder = CBAnalyticsAlertRequestCriteriaBuilder()
    
                        
class VMwareAlertSearchQuery(BaseAlertSearchQuery, CBAnalyticsAlertCriteriaBuilderMixin):
    """
    Represents a query that is used to locate VMwareAlert objects.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._criteria_builder = VMwareAlertRequestCriteriaBuilder()
    
                        
class BulkUpdateAlertsBase:
    """
    Base query for doing bulk updates on alerts, where the result of a search is used to set
    the states of multiple alerts.
    """
    def __init__(self, cb, state):
        self._cb = cb
        self._state = state
        self._additional_fields = {}
        
    def remediation(self, remediation):
        """
        Sets the remediation state message to be applied to all selected alerts.
        
        :param remediation str: The remediation state message.
        """
        self._additional_fields["remediation_state"] = remediation
        return self
    
    def comment(self, comment):
        """
        Sets the comment to be applied to all selected alerts.
        
        :param comment str: The comment to be used.
        """
        self._additional_fields["comment"] = comment
        return self
    
    def _url(self):
        raise ApiError("invalid abstract URL for the operation")
        
    def _build_request(self):
        request = self._additional_fields
        request["state"] = self._state
        return request
    
    def run(self):
        """
        Executes the search query and alert state change operation.
        
        :return: A WorkflowStatus object that can be used for monitoring the progress
                 of the operation.
        """
        resp = self._cb.post_object(self._url(), body=self._build_request())
        return self._cb._new_workflow_status(resp["request_id"])
        
        
class BulkUpdateAlerts(BulkUpdateAlertsBase, AlertCriteriaBuilderMixin, QueryBuilderSupportMixin):
    """
    Query for bulk update of base-level alerts.
    """
    def __init__(self, cb, state):
        super().__init__(cb, state)           
        self._criteria_builder = AlertRequestCriteriaBuilder()
        self._query_builder = QueryBuilder()
        
    def _url(self):
        return "/v6/orgs/{0}/alerts/workflow/_criteria".format(self._cb.credentials.org_key)

    def _build_request(self):
        request = super().build_request()
        request["criteria"] = self._criteria_builder.build()
        request["query"] = self._query_builder._collapse()
        return request
    
    
class BulkUpdateCBAnalyticsAlerts(BulkUpdateAlerts, CBAnalyticsAlertCriteriaBuilderMixin):    
    """
    Query for bulk update of CB Analytics alerts.
    """
    def __init__(self, cb, state):
        super().__init__(cb, state)           
        self._criteria_builder = CBAnalyticsAlertRequestCriteriaBuilder()

    def _url(self):
        return "/v6/orgs/{0}/alerts/cbanalytics/workflow/_criteria".format(self._cb.credentials.org_key)
    
    
class BulkUpdateVMwareAlerts(BulkUpdateAlerts, VMwareAlertCriteriaBuilderMixin):
    """
    Query for bulk update of VMware alerts.
    """
    def __init__(self, cb, state):
        super().__init__(cb, state)           
        self._criteria_builder = VMwareAlertRequestCriteriaBuilder()

    def _url(self):
        return "/v6/orgs/{0}/alerts/vmware/workflow/_criteria".format(self._cb.credentials.org_key)
    
    
class BulkUpdateWatchlistAlerts(BulkUpdateAlerts, WatchlistAlertCriteriaBuilderMixin):
    """
    Query for bulk update of watchlist alerts.
    """
    def __init__(self, cb, state):
        super().__init__(cb, state)           
        self._criteria_builder = WatchlistAlertRequestCriteriaBuilder()
        
    def _url(self):
        return "/v6/orgs/{0}/alerts/watchlist/workflow/_criteria".format(self._cb.credentials.org_key)
    
    
class BulkUpdateThreatAlerts(BulkUpdateAlertsBase):
    """
    Query for bulk update of threat alerts.
    """
    def __init__(self, cb, state):
        super().__init__(cb, state)           
        self._threat_ids = []
        
    def threat_ids(self, threats):
        """
        Specifies the threat IDs to set the status of alerts for.
        
        :param threats list: The list of string threat identifiers.
        :return: This instance.
        """
        if not all(isinstance(t, str) for t in threats):
            raise ApiError("One or more invalid threat ID values")
        self._threat_ids = self._threat_ids + threats
        return self

    def _url(self):
        return "/v6/orgs/{0}/threat/workflow/_criteria".format(self._cb.credentials.org_key)
    
    def _build_request(self):
        request = super()._build_request()
        request["threat_id"] = self._threat_ids
        return request
    