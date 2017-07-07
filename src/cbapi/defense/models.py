from ..models import MutableBaseModel, CreatableModelMixin, NewBaseModel

import logging
import json
from ..errors import ServerError

log = logging.getLogger(__name__)


class DefenseMutableModel(MutableBaseModel):
    _change_object_http_method = "PATCH"

    def _update_object(self):
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
                message = json.loads(request_ret.content)[0]
            except:
                message = request_ret.content

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
                        # "success" is False
                        raise ServerError(request_ret.status_code, message.get("message", ""),
                                          result="Did not update {0:s} record.".format(self.__class__.__name__))
            except:
                pass

        self._dirty_attributes = {}
        if refresh_required:
            self.refresh()
        return self._model_unique_id


class Device(DefenseMutableModel):
    urlobject = "/integrationServices/v3/device"
    primary_key = "deviceId"
    info_key = "deviceInfo"
    swagger_meta_file = "defense/models/deviceInfo.yaml"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Device, self).__init__(cb, model_unique_id, initial_data)

    def _parse(self, obj):
        if type(obj) == dict and "deviceInfo" in obj:
            return obj["deviceInfo"]

    def lr_session(self):
        """
        Retrieve a Live Response session object for this Device.

        :return: Live Response session object
        :rtype: :py:class:`cbapi.defense.cblr.LiveResponseSession`
        :raises ApiError: if there is an error establishing a Live Response session for this Device

        """
        return self._cb._request_lr_session(self._model_unique_id)


class Event(NewBaseModel):
    urlobject = "/integrationServices/v3/event"
    primary_key = "eventId"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Event, self).__init__(cb, model_unique_id, initial_data)

    def _parse(self, obj):
        if type(obj) == dict and "eventInfo" in obj:
            return obj["eventInfo"]

