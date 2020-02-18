from cbapi.errors import ApiError
from .base_query import PSCQueryBase, QueryBuilder, QueryBuilderSupportMixin, IterableQueryMixin


class DeviceSearchQuery(PSCQueryBase, QueryBuilderSupportMixin, IterableQueryMixin):
    """
    Represents a query that is used to locate Device objects.
    """
    VALID_OS = ["WINDOWS", "ANDROID", "MAC", "IOS", "LINUX", "OTHER"]
    VALID_STATUSES = ["PENDING", "REGISTERED", "UNINSTALLED", "DEREGISTERED",
                      "ACTIVE", "INACTIVE", "ERROR", "ALL", "BYPASS_ON",
                      "BYPASS", "QUARANTINE", "SENSOR_OUTOFDATE",
                      "DELETED", "LIVE"]
    VALID_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "MISSION_CRITICAL"]
    VALID_DIRECTIONS = ["ASC", "DESC"]

    def __init__(self, doc_class, cb):
        super().__init__(doc_class, cb)
        self._query_builder = QueryBuilder()
        self._criteria = {}
        self._time_filter = {}
        self._exclusions = {}
        self._sortcriteria = {}

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

    def _update_exclusions(self, key, newlist):
        """
        Updates the exclusion criteria being collected for a query. Assumes the specified criteria item is
        defined as a list; the list passed in will be set as the value for this criteria item, or
        appended to the existing one if there is one.

        :param str key: The key for the criteria item to be set
        :param list newlist: List of values to be set for the criteria item
        """
        oldlist = self._exclusions.get(key, [])
        self._exclusions[key] = oldlist + newlist

    def set_ad_group_ids(self, ad_group_ids):
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

    def set_device_ids(self, device_ids):
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

    def set_last_contact_time(self, *args, **kwargs):
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

    def set_os(self, operating_systems):
        """
        Restricts the devices that this query is performed on to the specified
        operating systems.

        :param operating_systems: list of operating systems
        :return: This instance
        """
        if not all((osval in DeviceSearchQuery.VALID_OS) for osval in operating_systems):
            raise ApiError("One or more invalid operating systems")
        self._update_criteria("os", operating_systems)
        return self

    def set_policy_ids(self, policy_ids):
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

    def set_status(self, statuses):
        """
        Restricts the devices that this query is performed on to the specified
        status values.

        :param statuses: list of strings
        :return: This instance
        """
        if not all((stat in DeviceSearchQuery.VALID_STATUSES) for stat in statuses):
            raise ApiError("One or more invalid status values")
        self._update_criteria("status", statuses)
        return self

    def set_target_priorities(self, target_priorities):
        """
        Restricts the devices that this query is performed on to the specified
        target priority values.

        :param target_priorities: list of strings
        :return: This instance
        """
        if not all((prio in DeviceSearchQuery.VALID_PRIORITIES) for prio in target_priorities):
            raise ApiError("One or more invalid target priority values")
        self._update_criteria("target_priority", target_priorities)
        return self

    def set_exclude_sensor_versions(self, sensor_versions):
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
        if direction not in DeviceSearchQuery.VALID_DIRECTIONS:
            raise ApiError("invalid sort direction specified")
        self._sortcriteria = {"field": key, "order": direction}
        return self

    def _build_request(self, from_row, max_rows):
        """
        Creates the request body for an API call.

        :param int from_row: The row to start the query at.
        :param int max_rows: The maximum number of rows to be returned.
        :return: A dict containing the complete request body.
        """
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

    def download(self):
        """
        Uses the query parameters that have been set to download all
        device listings in CSV format.

        Example::

        >>> cb.select(Device).set_status(["ALL"]).download()

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
        """
        Perform a bulk action on all devices matching the current search criteria.

        :param str action_type: The action type to be performed.
        :param dict options: Options for the bulk device action.  Default None.
        """
        request = {"action_type": action_type, "search": self._build_request(0, -1)}
        if options:
            request["options"] = options
        return self._cb._raw_device_action(request)

    def background_scan(self, scan):
        """
        Set the background scan option for the specified devices.

        :param boolean scan: True to turn background scan on, False to turn it off.
        """
        return self._bulk_device_action("BACKGROUND_SCAN", self._cb._action_toggle(scan))

    def bypass(self, enable):
        """
        Set the bypass option for the specified devices.

        :param boolean enable: True to enable bypass, False to disable it.
        """
        return self._bulk_device_action("BYPASS", self._cb._action_toggle(enable))

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

    def quarantine(self, enable):
        """
        Set the quarantine option for the specified devices.

        :param boolean enable: True to enable quarantine, False to disable it.
        """
        return self._bulk_device_action("QUARANTINE", self._cb._action_toggle(enable))

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
        return self._bulk_device_action("UPDATE_SENSOR_VERSION", {"sensor_version": sensor_version})
