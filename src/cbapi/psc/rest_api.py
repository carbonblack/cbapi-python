from cbapi.connection import BaseAPI
from cbapi.errors import ApiError, ServerError
from .cblr import LiveResponseSessionManager
from .models import Device
from .query import BulkUpdateAlerts, BulkUpdateWatchlistAlerts, BulkUpdateThreatAlerts
import logging

log = logging.getLogger(__name__)


class CbPSCBaseAPI(BaseAPI):
    """The main entry point into the Cb PSC API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi import CbPSCBaseAPI
    >>> cb = CbPSCBaseAPI(profile="production")
    """
    alert_update_queries = {"ALERT": BulkUpdateAlerts, "WATCHLIST": BulkUpdateWatchlistAlerts,
                            "THREAT": BulkUpdateThreatAlerts}
    
    def __init__(self, *args, **kwargs):
        super(CbPSCBaseAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

    def _perform_query(self, cls, **kwargs):
        if hasattr(cls, "_query_implementation"):
            return cls._query_implementation(self)
        else:
            raise ApiError("All PSC models should provide _query_implementation")

    # ---- LiveOps

    @property
    def live_response(self):
        if self._lr_scheduler is None:
            self._lr_scheduler = LiveResponseSessionManager(self)
        return self._lr_scheduler

    def _request_lr_session(self, sensor_id):
        return self.live_response.request_session(sensor_id)

    # ---- Device API

    def get_device(self, device_id):
        """
        Locate a device with the specified device ID.

        :param int device_id: The ID of the device to look up.
        :return: The new device object.
        """
        return Device(self, device_id)

    def _raw_device_action(self, request):
        url = "/appservices/v6/orgs/{0}/device_actions".format(self.credentials.org_key)
        resp = self.post_object(url, body=request)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 204:
            return None
        else:
            raise ServerError(error_code=resp.status_code, message="Device action error: {0}".format(resp.content))

    def _device_action(self, device_ids, action_type, options=None):
        request = {"action_type": action_type, "device_id": device_ids}
        if options:
            request["options"] = options
        return self._raw_device_action(request)

    def _action_toggle(self, flag):
        if flag:
            return {"toggle": "ON"}
        else:
            return {"toggle": "OFF"}

    def device_background_scan(self, device_ids, flag):
        """
        Set the background scan option for the specified devices.

        :param list device_ids: List of IDs of devices to be set.
        :param boolean flag: True to turn background scan on, False to turn it off.
        """
        return self._device_action(device_ids, "BACKGROUND_SCAN", self._action_toggle(flag))

    def device_bypass(self, device_ids, flag):
        """
        Set the bypass option for the specified devices.

        :param list device_ids: List of IDs of devices to be set.
        :param boolean flag: True to enable bypass, False to disable it.
        """
        return self._device_action(device_ids, "BYPASS", self._action_toggle(flag))

    def device_delete_sensor(self, device_ids):
        """
        Delete the specified sensor devices.

        :param list device_ids: List of IDs of devices to be deleted.
        """
        return self._device_action(device_ids, "DELETE_SENSOR")

    def device_uninstall_sensor(self, device_ids):
        """
        Uninstall the specified sensor devices.

        :param list device_ids: List of IDs of devices to be uninstalled.
        """
        return self._device_action(device_ids, "UNINSTALL_SENSOR")

    def device_quarantine(self, device_ids, flag):
        """
        Set the quarantine option for the specified devices.

        :param list device_ids: List of IDs of devices to be set.
        :param boolean flag: True to enable quarantine, False to disable it.
        """
        return self._device_action(device_ids, "QUARANTINE", self._action_toggle(flag))

    def device_update_policy(self, device_ids, policy_id):
        """
        Set the current policy for the specified devices.

        :param list device_ids: List of IDs of devices to be changed.
        :param int policy_id: ID of the policy to set for the devices.
        """
        return self._device_action(device_ids, "UPDATE_POLICY", {"policy_id": policy_id})

    def device_update_sensor_version(self, device_ids, sensor_version):
        """
        Update the sensor version for the specified devices.

        :param list device_ids: List of IDs of devices to be changed.
        :param dict sensor_version: New version properties for the sensor.
        """
        return self._device_action(device_ids, "UPDATE_SENSOR_VERSION", {"sensor_version": sensor_version})
    
    # ---- Alerts API
    
    def _bulk_alert_update_query(self, state, querytype):
        cls = CbPSCBaseAPI.alert_update_queries.get(querytype, None)
        if cls is None:
            raise ApiError("unknown query type for bulk alert update")
        return cls(self, state)
    
    def bulk_alert_dismiss(self, querytype):
        return self._bulk_alert_update_query("DISMISSED", querytype)
    
    def bulk_alert_undismiss(self, querytype):
        return self._bulk_alert_update_query("OPEN", querytype)
    