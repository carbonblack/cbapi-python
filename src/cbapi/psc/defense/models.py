from cbapi.models import MutableBaseModel, CreatableModelMixin, NewBaseModel

from copy import deepcopy
import logging
import json

from cbapi.errors import ServerError

log = logging.getLogger(__name__)


class DefenseMutableModel(MutableBaseModel):
    _change_object_http_method = "PATCH"
    _change_object_key_name = None

    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=False):
        super(DefenseMutableModel, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
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


class Device(DefenseMutableModel):
    urlobject = "/integrationServices/v3/device"
    primary_key = "deviceId"
    info_key = "deviceInfo"
    swagger_meta_file = "psc/defense/models/deviceInfo.yaml"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Device, self).__init__(cb, model_unique_id, initial_data)

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
    info_key = "eventInfo"

    def _parse(self, obj):
        if type(obj) == dict and self.info_key in obj:
            return obj[self.info_key]

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Event, self).__init__(cb, model_unique_id, initial_data)


class Policy(DefenseMutableModel, CreatableModelMixin):
    urlobject = "/integrationServices/v3/policy"
    info_key = "policyInfo"
    swagger_meta_file = "psc/defense/models/policyInfo.yaml"
    _change_object_http_method = "PUT"
    _change_object_key_name = "policyId"

    @property
    def rules(self):
        return dict([(r.get("id"), r) for r in self.policy.get("rules", [])])

    def add_rule(self, new_rule):
        self._cb.post_object("{0}/rule".format(self._build_api_request_uri()), {"ruleInfo": new_rule})
        self.refresh()

    def delete_rule(self, rule_id):
        self._cb.delete_object("{0}/rule/{1}".format(self._build_api_request_uri(), rule_id))
        self.refresh()

    def replace_rule(self, rule_id, new_rule):
        self._cb.put_object("{0}/rule/{1}".format(self._build_api_request_uri(), rule_id),
                            {"ruleInfo": new_rule})
        self.refresh()
