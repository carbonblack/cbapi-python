from cbapi.models import MutableBaseModel, UnrefreshableModel
from cbapi.errors import ServerError
from cbapi.psc.devices_query import DeviceSearchQuery

from copy import deepcopy
import logging
import json
import time

log = logging.getLogger(__name__)


class PSCMutableModel(MutableBaseModel):
    _change_object_http_method = "PATCH"
    _change_object_key_name = None

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=False):
        super(PSCMutableModel, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                              force_init=force_init, full_doc=full_doc)
        if not self._change_object_key_name:
            self._change_object_key_name = self.primary_key

    def _parse(self, obj):
        if type(obj) == dict and self.info_key in obj:
            return obj[self.info_key]

    def _update_object(self):
        if self._change_object_http_method != "PATCH":
            return self._update_entire_object()
        else:
            return self._patch_object()

    def _update_entire_object(self):
        if self.__class__.primary_key in self._dirty_attributes.keys() or self._model_unique_id is None:
            new_object_info = deepcopy(self._info)
            try:
                if not self._new_object_needs_primary_key:
                    del(new_object_info[self.__class__.primary_key])
            except Exception:
                pass
            log.debug("Creating a new {0:s} object".format(self.__class__.__name__))
            ret = self._cb.api_json_request(self.__class__._new_object_http_method, self.urlobject,
                                            data={self.info_key: new_object_info})
        else:
            log.debug("Updating {0:s} with unique ID {1:s}".format(self.__class__.__name__, str(self._model_unique_id)))
            ret = self._cb.api_json_request(self.__class__._change_object_http_method,
                                            self._build_api_request_uri(), data={self.info_key: self._info})

        return self._refresh_if_needed(ret)

    def _patch_object(self):
        if self.__class__.primary_key in self._dirty_attributes.keys() or self._model_unique_id is None:
            log.debug("Creating a new {0:s} object".format(self.__class__.__name__))
            ret = self._cb.api_json_request(self.__class__._new_object_http_method, self.urlobject,
                                            data=self._info)
        else:
            updates = {}
            for k in self._dirty_attributes.keys():
                updates[k] = self._info[k]
            log.debug("Updating {0:s} with unique ID {1:s}".format(self.__class__.__name__, str(self._model_unique_id)))
            ret = self._cb.api_json_request(self.__class__._change_object_http_method,
                                            self._build_api_request_uri(), data=updates)

        return self._refresh_if_needed(ret)

    def _refresh_if_needed(self, request_ret):
        refresh_required = True

        if request_ret.status_code not in range(200, 300):
            try:
                message = json.loads(request_ret.text)[0]
            except Exception:
                message = request_ret.text

            raise ServerError(request_ret.status_code, message,
                              result="Did not update {} record.".format(self.__class__.__name__))
        else:
            try:
                message = request_ret.json()
                log.debug("Received response: %s" % message)
                if not isinstance(message, dict):
                    raise ServerError(request_ret.status_code, message,
                                      result="Unknown error updating {0:s} record.".format(self.__class__.__name__))
                else:
                    if message.get("success", False):
                        if isinstance(message.get(self.info_key, None), dict):
                            self._info = message.get(self.info_key)
                            self._full_init = True
                            refresh_required = False
                        else:
                            if self._change_object_key_name in message.keys():
                                # if all we got back was an ID, try refreshing to get the entire record.
                                log.debug("Only received an ID back from the server, forcing a refresh")
                                self._info[self.primary_key] = message[self._change_object_key_name]
                                refresh_required = True
                    else:
                        # "success" is False
                        raise ServerError(request_ret.status_code, message.get("message", ""),
                                          result="Did not update {0:s} record.".format(self.__class__.__name__))
            except Exception:
                pass

        self._dirty_attributes = {}
        if refresh_required:
            self.refresh()
        return self._model_unique_id


class Device(PSCMutableModel):
    urlobject = "/appservices/v6/orgs/{0}/devices"
    urlobject_single = "/appservices/v6/orgs/{0}/devices/{1}"
    primary_key = "id"
    swagger_meta_file = "psc/models/device.yaml"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Device, self).__init__(cb, model_unique_id, initial_data)
        if model_unique_id is not None and initial_data is None:
            self._refresh()

    @classmethod
    def _query_implementation(cls, cb):
        return DeviceSearchQuery(cls, cb)

    def _refresh(self):
        url = self.urlobject_single.format(self._cb.credentials.org_key, self._model_unique_id)
        resp = self._cb.get_object(url)
        self._info = resp
        self._last_refresh_time = time.time()
        return True

    def background_scan(self, flag):
        """
        Set the background scan option for this device.

        :param boolean flag: True to turn background scan on, False to turn it off.
        """
        return self._cb.device_background_scan([self._model_unique_id], flag)

    def bypass(self, flag):
        """
        Set the bypass option for this device.

        :param boolean flag: True to enable bypass, False to disable it.
        """
        return self._cb.device_bypass([self._model_unique_id], flag)

    def delete_sensor(self):
        """
        Delete this sensor device.
        """
        return self._cb.device_delete_sensor([self._model_unique_id])

    def uninstall_sensor(self):
        """
        Uninstall this sensor device.
        """
        return self._cb.device_uninstall_sensor([self._model_unique_id])

    def quarantine(self, flag):
        """
        Set the quarantine option for this device.

        :param boolean flag: True to enable quarantine, False to disable it.
        """
        return self._cb.device_quarantine([self._model_unique_id], flag)

    def update_policy(self, policy_id):
        """
        Set the current policy for this device.

        :param int policy_id: ID of the policy to set for the devices.
        """
        return self._cb.device_update_policy([self._model_unique_id], policy_id)

    def update_sensor_version(self, sensor_version):
        """
        Update the sensor version for this device.

        :param dict sensor_version: New version properties for the sensor.
        """
        return self._cb.device_update_sensor_version([self._model_unique_id], sensor_version)
