from ..models import MutableBaseModel, CreatableModelMixin, NewBaseModel


class Device(NewBaseModel):
    urlobject = "/integrationServices/v3/device"
    primary_key = "deviceId"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Device, self).__init__(cb, model_unique_id, initial_data)

    def _parse(self, obj):
        if type(obj) == dict and "deviceInfo" in obj:
            return obj["deviceInfo"]


class Event(NewBaseModel):
    urlobject = "/integrationServices/v3/event"
    primary_key = "eventId"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Event, self).__init__(cb, model_unique_id, initial_data)

    def _parse(self, obj):
        if type(obj) == dict and "eventInfo" in obj:
            return obj["eventInfo"]

