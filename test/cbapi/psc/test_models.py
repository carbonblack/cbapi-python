import pytest
from cbapi.psc.models import Device
from cbapi.psc.rest_api import CbPSCBaseAPI
from test.cbtest import StubResponse, patch_cbapi


class StubScheduler:
    def __init__(self, expected_id):
        self.expected_id = expected_id
        self.was_called = False

    def request_session(self, sensor_id):
        assert sensor_id == self.expected_id
        self.was_called = True
        return {"itworks": True}


def test_Device_lr_session(monkeypatch):

    def _get_session(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    sked = StubScheduler(6023)
    api._lr_scheduler = sked
    patch_cbapi(monkeypatch, api, GET=_get_session)
    dev = Device(api, 6023, {"id": 6023})
    sess = dev.lr_session()
    assert sess["itworks"]
    assert sked.was_called


def test_Device_background_scan(monkeypatch):
    _was_called = False

    def _get_device(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    def _background_scan(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "BACKGROUND_SCAN", "device_id": [6023], "options": {"toggle": "ON"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device, POST=_background_scan)
    dev = Device(api, 6023, {"id": 6023})
    dev.background_scan(True)
    assert _was_called


def test_Device_bypass(monkeypatch):
    _was_called = False

    def _get_device(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    def _bypass(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "BYPASS", "device_id": [6023], "options": {"toggle": "OFF"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device, POST=_bypass)
    dev = Device(api, 6023, {"id": 6023})
    dev.bypass(False)
    assert _was_called


def test_Device_delete_sensor(monkeypatch):
    _was_called = False

    def _get_device(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    def _delete_sensor(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "DELETE_SENSOR", "device_id": [6023]}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device, POST=_delete_sensor)
    dev = Device(api, 6023, {"id": 6023})
    dev.delete_sensor()
    assert _was_called


def test_Device_uninstall_sensor(monkeypatch):
    _was_called = False

    def _get_device(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    def _uninstall_sensor(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UNINSTALL_SENSOR", "device_id": [6023]}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device, POST=_uninstall_sensor)
    dev = Device(api, 6023, {"id": 6023})
    dev.uninstall_sensor()
    assert _was_called


def test_Device_quarantine(monkeypatch):
    _was_called = False

    def _get_device(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    def _quarantine(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "QUARANTINE", "device_id": [6023], "options": {"toggle": "ON"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device, POST=_quarantine)
    dev = Device(api, 6023, {"id": 6023})
    dev.quarantine(True)
    assert _was_called


def test_Device_update_policy(monkeypatch):
    _was_called = False

    def _get_device(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    def _update_policy(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UPDATE_POLICY", "device_id": [6023], "options": {"policy_id": 8675309}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device, POST=_update_policy)
    dev = Device(api, 6023, {"id": 6023})
    dev.update_policy(8675309)
    assert _was_called


def test_Device_update_sensor_version(monkeypatch):
    _was_called = False

    def _get_device(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return {"id": 6023}

    def _update_sensor_version(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UPDATE_SENSOR_VERSION", "device_id": [6023],
                        "options": {"sensor_version": {"RHEL": "2.3.4.5"}}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device, POST=_update_sensor_version)
    dev = Device(api, 6023, {"id": 6023})
    dev.update_sensor_version({"RHEL": "2.3.4.5"})
    assert _was_called
