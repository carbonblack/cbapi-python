from cbapi.errors import ApiError
from .base_query import PSCQueryBase, QueryBuilder, QueryBuilderSupportMixin, IterableQueryMixin
from .devices_query import DeviceSearchQuery


class BaseAlertSearchQuery(PSCQueryBase, QueryBuilderSupportMixin, IterableQueryMixin):
    """
    Represents a query that is used to locate BaseAlert objects.
    """
    VALID_CATEGORIES = ["THREAT", "MONITORED", "INFO", "MINOR", "SERIOUS", "CRITICAL"]
    VALID_REPUTATIONS = ["KNOWN_MALWARE", "SUSPECT_MALWARE", "PUP", "NOT_LISTED", "ADAPTIVE_WHITE_LIST",
                         "COMMON_WHITE_LIST", "TRUSTED_WHITE_LIST", "COMPANY_BLACK_LIST"]
    VALID_ALERT_TYPES = ["CB_ANALYTICS", "VMWARE", "WATCHLIST"]
    VALID_WORKFLOW_VALS = ["OPEN", "DISMISSED"]
    VALID_FACET_FIELDS = ["ALERT_TYPE", "CATEGORY", "REPUTATION", "WORKFLOW", "TAG", "POLICY_ID",
                          "POLICY_NAME", "DEVICE_ID", "DEVICE_NAME", "APPLICATION_HASH",
                          "APPLICATION_NAME", "STATUS", "RUN_STATE", "POLICY_APPLIED_STATE",
                          "POLICY_APPLIED", "SENSOR_ACTION"]

    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._criteria = {}
        self._time_filter = {}
        self._sortcriteria = {}
        self._bulkupdate_url = "/appservices/v6/orgs/{0}/alerts/workflow/_criteria"
        self._count_valid = False
        self._total_results = 0

    def _update_criteria(self, key, newlist):
        """
        Updates the criteria being collected for a query. Assumes the specified criteria item is
        defined as a list; the list passed in will be set as the value for this criteria item, or
        appended to the existing one if there is one.

        :param str key: The key for the criteria item to be set
        :param list newlist: List of values to be set for the criteria item
        """
        oldlist = self._criteria.get(key, [])
        self._criteria[key] = oldlist + newlist

    def set_categories(self, categories):
        """
        Restricts the alerts that this query is performed on to the specified categories.

        :param categories list: List of categories to be restricted to. Valid categories are
                                "THREAT", "MONITORED", "INFO", "MINOR", "SERIOUS", and "CRITICAL."
        :return: This instance
        """
        if not all((c in BaseAlertSearchQuery.VALID_CATEGORIES) for c in categories):
            raise ApiError("One or more invalid category values")
        self._update_criteria("category", categories)
        return self

    def set_create_time(self, *args, **kwargs):
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

    def set_device_ids(self, device_ids):
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

    def set_device_names(self, device_names):
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

    def set_device_os(self, device_os):
        """
        Restricts the alerts that this query is performed on to the specified
        device operating systems.

        :param device_os list: List of string operating systems.  Valid values are
                               "WINDOWS", "ANDROID", "MAC", "IOS", "LINUX", and "OTHER."
        :return: This instance
        """
        if not all((osval in DeviceSearchQuery.VALID_OS) for osval in device_os):
            raise ApiError("One or more invalid operating systems")
        self._update_criteria("device_os", device_os)
        return self

    def set_device_os_versions(self, device_os_versions):
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

    def set_device_username(self, users):
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

    def set_group_results(self, do_group):
        """
        Specifies whether or not to group the results of the query.

        :param do_group boolean: True to group the results, False to not do so.
        :return: This instance
        """
        self._criteria["group_results"] = True if do_group else False
        return self

    def set_alert_ids(self, alert_ids):
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

    def set_legacy_alert_ids(self, alert_ids):
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

    def set_minimum_severity(self, severity):
        """
        Restricts the alerts that this query is performed on to the specified
        minimum severity level.

        :param severity int: The minimum severity level for alerts.
        :return: This instance
        """
        self._criteria["minimum_severity"] = severity
        return self

    def set_policy_ids(self, policy_ids):
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

    def set_policy_names(self, policy_names):
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

    def set_process_names(self, process_names):
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

    def set_process_sha256(self, shas):
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

    def set_reputations(self, reps):
        """
        Restricts the alerts that this query is performed on to the specified
        reputation values.

        :param reps list: List of string reputation values.  Valid values are
                          "KNOWN_MALWARE", "SUSPECT_MALWARE", "PUP", "NOT_LISTED",
                          "ADAPTIVE_WHITE_LIST", "COMMON_WHITE_LIST",
                          "TRUSTED_WHITE_LIST", and "COMPANY_BLACK_LIST".
        :return: This instance
        """
        if not all((r in BaseAlertSearchQuery.VALID_REPUTATIONS) for r in reps):
            raise ApiError("One or more invalid reputation values")
        self._update_criteria("reputation", reps)
        return self

    def set_tags(self, tags):
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

    def set_target_priorities(self, priorities):
        """
        Restricts the alerts that this query is performed on to the specified
        target priority values.

        :param priorities list: List of string target priority values.  Valid values are
                                "LOW", "MEDIUM", "HIGH", and "MISSION_CRITICAL".
        :return: This instance
        """
        if not all((prio in DeviceSearchQuery.VALID_PRIORITIES) for prio in priorities):
            raise ApiError("One or more invalid priority values")
        self._update_criteria("target_value", priorities)
        return self

    def set_threat_ids(self, threats):
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

    def set_types(self, alerttypes):
        """
        Restricts the alerts that this query is performed on to the specified
        alert type values.

        :param alerttypes list: List of string alert type values.  Valid values are
                                "CB_ANALYTICS", "VMWARE", and "WATCHLIST".
        :return: This instance
        """
        if not all((t in BaseAlertSearchQuery.VALID_ALERT_TYPES) for t in alerttypes):
            raise ApiError("One or more invalid alert type values")
        self._update_criteria("type", alerttypes)
        return self

    def set_workflows(self, workflow_vals):
        """
        Restricts the alerts that this query is performed on to the specified
        workflow status values.

        :param workflow_vals list: List of string alert type values.  Valid values are
                                   "OPEN" and "DISMISSED".
        :return: This instance
        """
        if not all((t in BaseAlertSearchQuery.VALID_WORKFLOW_VALS) for t in workflow_vals):
            raise ApiError("One or more invalid workflow status values")
        self._update_criteria("workflow", workflow_vals)
        return self

    def _build_criteria(self):
        """
        Builds the criteria object for use in a query.

        :return: The criteria object.
        """
        mycrit = self._criteria
        if self._time_filter:
            mycrit["create_time"] = self._time_filter
        return mycrit

    def sort_by(self, key, direction="ASC"):
        """Sets the sorting behavior on a query's results.

        Example::

        >>> cb.select(BaseAlert).sort_by("name")

        :param key: the key in the schema to sort by
        :param direction: the sort order, either "ASC" or "DESC"
        :rtype: :py:class:`BaseAlertSearchQuery`
        """
        if direction not in DeviceSearchQuery.VALID_DIRECTIONS:
            raise ApiError("invalid sort direction specified")
        self._sortcriteria = {"field": key, "order": direction}
        return self

    def _build_request(self, from_row, max_rows, add_sort=True):
        """
        Creates the request body for an API call.

        :param int from_row: The row to start the query at.
        :param int max_rows: The maximum number of rows to be returned.
        :param boolean add_sort: If True(default), the sort criteria will be added as part of the request.
        :return: A dict containing the complete request body.
        """
        request = {"criteria": self._build_criteria()}
        request["query"] = self._query_builder._collapse()
        request["rows"] = 100
        if from_row > 0:
            request["start"] = from_row
        if max_rows >= 0:
            request["rows"] = max_rows
        if add_sort and self._sortcriteria != {}:
            request["sort"] = [self._sortcriteria]
        return request

    def _build_url(self, tail_end):
        """
        Creates the URL to be used for an API call.

        :param str tail_end: String to be appended to the end of the generated URL.
        """
        url = self._doc_class.urlobject.format(self._cb.credentials.org_key) + tail_end
        return url

    def _count(self):
        """
        Returns the number of results from the run of this query.

        :return: The number of results from the run of this query.
        """
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
        """
        Performs the query and returns the results of the query in an iterable fashion.

        :param int from_row: The row to start the query at (default 0).
        :param int max_rows: The maximum number of rows to be returned (default -1, meaning "all").
        """
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
        if not all((field in BaseAlertSearchQuery.VALID_FACET_FIELDS) for field in fieldlist):
            raise ApiError("One or more invalid term field names")
        request = self._build_request(0, -1, False)
        request["terms"] = {"fields": fieldlist, "rows": max_rows}
        url = self._build_url("/_facet")
        resp = self._cb.post_object(url, body=request)
        result = resp.json()
        return result.get("results", [])

    def _update_status(self, status, remediation, comment):
        """
        Updates the status of all alerts matching the given query.

        :param str state: The status to put the alerts into, either "OPEN" or "DISMISSED".
        :param remediation str: The remediation state to set for all alerts.
        :param comment str: The comment to set for all alerts.
        :return: The request ID, which may be used to select a WorkflowStatus object.
        """
        request = {"state": status, "criteria": self._build_criteria(), "query": self._query_builder._collapse()}
        if remediation is not None:
            request["remediation_state"] = remediation
        if comment is not None:
            request["comment"] = comment
        resp = self._cb.post_object(self._bulkupdate_url.format(self._cb.credentials.org_key), body=request)
        output = resp.json()
        return output["request_id"]

    def update(self, remediation=None, comment=None):
        """
        Update all alerts matching the given query. The alerts will be left in an OPEN state after this request.

        :param remediation str: The remediation state to set for all alerts.
        :param comment str: The comment to set for all alerts.
        :return: The request ID, which may be used to select a WorkflowStatus object.
        """
        return self._update_status("OPEN", remediation, comment)

    def dismiss(self, remediation=None, comment=None):
        """
        Dismiss all alerts matching the given query. The alerts will be left in a DISMISSED state after this request.

        :param remediation str: The remediation state to set for all alerts.
        :param comment str: The comment to set for all alerts.
        :return: The request ID, which may be used to select a WorkflowStatus object.
        """
        return self._update_status("DISMISSED", remediation, comment)


class WatchlistAlertSearchQuery(BaseAlertSearchQuery):
    """
    Represents a query that is used to locate WatchlistAlert objects.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._bulkupdate_url = "/appservices/v6/orgs/{0}/alerts/watchlist/workflow/_criteria"

    def set_watchlist_ids(self, ids):
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

    def set_watchlist_names(self, names):
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


class CBAnalyticsAlertSearchQuery(BaseAlertSearchQuery):
    """
    Represents a query that is used to locate CBAnalyticsAlert objects.
    """
    VALID_THREAT_CATEGORIES = ["UNKNOWN", "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", "RISKY_PROGRAM"]
    VALID_LOCATIONS = ["ONSITE", "OFFSITE", "UNKNOWN"]
    VALID_KILL_CHAIN_STATUSES = ["RECONNAISSANCE", "WEAPONIZE", "DELIVER_EXPLOIT", "INSTALL_RUN",
                                 "COMMAND_AND_CONTROL", "EXECUTE_GOAL", "BREACH"]
    VALID_POLICY_APPLIED = ["APPLIED", "NOT_APPLIED"]
    VALID_RUN_STATES = ["DID_NOT_RUN", "RAN", "UNKNOWN"]
    VALID_SENSOR_ACTIONS = ["POLICY_NOT_APPLIED", "ALLOW", "ALLOW_AND_LOG", "TERMINATE", "DENY"]
    VALID_THREAT_CAUSE_VECTORS = ["EMAIL", "WEB", "GENERIC_SERVER", "GENERIC_CLIENT", "REMOTE_DRIVE",
                                  "REMOVABLE_MEDIA", "UNKNOWN", "APP_STORE", "THIRD_PARTY"]

    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._bulkupdate_url = "/appservices/v6/orgs/{0}/alerts/cbanalytics/workflow/_criteria"

    def set_blocked_threat_categories(self, categories):
        """
        Restricts the alerts that this query is performed on to the specified
        threat categories that were blocked.

        :param categories list: List of threat categories to look for.  Valid values are "UNKNOWN",
                                "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", and "RISKY_PROGRAM".
        :return: This instance.
        """
        if not all((category in CBAnalyticsAlertSearchQuery.VALID_THREAT_CATEGORIES)
                   for category in categories):
            raise ApiError("One or more invalid threat categories")
        self._update_criteria("blocked_threat_category", categories)
        return self

    def set_device_locations(self, locations):
        """
        Restricts the alerts that this query is performed on to the specified
        device locations.

        :param locations list: List of device locations to look for. Valid values are "ONSITE", "OFFSITE",
                               and "UNKNOWN".
        :return: This instance.
        """
        if not all((location in CBAnalyticsAlertSearchQuery.VALID_LOCATIONS)
                   for location in locations):
            raise ApiError("One or more invalid device locations")
        self._update_criteria("device_location", locations)
        return self

    def set_kill_chain_statuses(self, statuses):
        """
        Restricts the alerts that this query is performed on to the specified
        kill chain statuses.

        :param statuses list: List of kill chain statuses to look for. Valid values are "RECONNAISSANCE",
                              "WEAPONIZE", "DELIVER_EXPLOIT", "INSTALL_RUN","COMMAND_AND_CONTROL",
                              "EXECUTE_GOAL", and "BREACH".
        :return: This instance.
        """
        if not all((status in CBAnalyticsAlertSearchQuery.VALID_KILL_CHAIN_STATUSES)
                   for status in statuses):
            raise ApiError("One or more invalid kill chain status values")
        self._update_criteria("kill_chain_status", statuses)
        return self

    def set_not_blocked_threat_categories(self, categories):
        """
        Restricts the alerts that this query is performed on to the specified
        threat categories that were NOT blocked.

        :param categories list: List of threat categories to look for.  Valid values are "UNKNOWN",
                                "NON_MALWARE", "NEW_MALWARE", "KNOWN_MALWARE", and "RISKY_PROGRAM".
        :return: This instance.
        """
        if not all((category in CBAnalyticsAlertSearchQuery.VALID_THREAT_CATEGORIES)
                   for category in categories):
            raise ApiError("One or more invalid threat categories")
        self._update_criteria("not_blocked_threat_category", categories)
        return self

    def set_policy_applied(self, applied_statuses):
        """
        Restricts the alerts that this query is performed on to the specified
        status values showing whether policies were applied.

        :param applied_statuses list: List of status values to look for. Valid values are
                                      "APPLIED" and "NOT_APPLIED".
        :return: This instance.
        """
        if not all((s in CBAnalyticsAlertSearchQuery.VALID_POLICY_APPLIED)
                   for s in applied_statuses):
            raise ApiError("One or more invalid policy-applied values")
        self._update_criteria("policy_applied", applied_statuses)
        return self

    def set_reason_code(self, reason):
        """
        Restricts the alerts that this query is performed on to the specified
        reason codes (enum values).

        :param reason list: List of string reason codes to look for.
        :return: This instance.
        """
        if not all(isinstance(t, str) for t in reason):
            raise ApiError("One or more invalid reason code values")
        self._update_criteria("reason_code", reason)
        return self

    def set_run_states(self, states):
        """
        Restricts the alerts that this query is performed on to the specified run states.

        :param states list: List of run states to look for. Valid values are "DID_NOT_RUN", "RAN",
                            and "UNKNOWN".
        :return: This instance.
        """
        if not all((s in CBAnalyticsAlertSearchQuery.VALID_RUN_STATES)
                   for s in states):
            raise ApiError("One or more invalid run states")
        self._update_criteria("run_state", states)
        return self

    def set_sensor_actions(self, actions):
        """
        Restricts the alerts that this query is performed on to the specified sensor actions.

        :param actions list: List of sensor actions to look for. Valid values are "POLICY_NOT_APPLIED",
                             "ALLOW", "ALLOW_AND_LOG", "TERMINATE", and "DENY".
        :return: This instance.
        """
        if not all((action in CBAnalyticsAlertSearchQuery.VALID_SENSOR_ACTIONS)
                   for action in actions):
            raise ApiError("One or more invalid sensor actions")
        self._update_criteria("sensor_action", actions)
        return self

    def set_threat_cause_vectors(self, vectors):
        """
        Restricts the alerts that this query is performed on to the specified threat cause vectors.

        :param vectors list: List of threat cause vectors to look for.  Valid values are "EMAIL", "WEB",
                             "GENERIC_SERVER", "GENERIC_CLIENT", "REMOTE_DRIVE", "REMOVABLE_MEDIA",
                             "UNKNOWN", "APP_STORE", and "THIRD_PARTY".
        :return: This instance.
        """
        if not all((vector in CBAnalyticsAlertSearchQuery.VALID_THREAT_CAUSE_VECTORS)
                   for vector in vectors):
            raise ApiError("One or more invalid threat cause vectors")
        self._update_criteria("threat_cause_vector", vectors)
        return self


class VMwareAlertSearchQuery(BaseAlertSearchQuery):
    """
    Represents a query that is used to locate VMwareAlert objects.
    """
    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._bulkupdate_url = "/appservices/v6/orgs/{0}/alerts/vmware/workflow/_criteria"

    def set_group_ids(self, groupids):
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
