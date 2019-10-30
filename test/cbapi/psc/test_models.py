import pytest
from cbapi.psc.models import Device
from cbapi.psc.rest_api import CbPSCBaseAPI
from test.mocks import MockResponse, ConnectionMocks

class MockScheduler:
    def __init__(self, expected_id):
        self.expected_id = expected_id
        self.was_called = False
        
    def request_session(self, sensor_id):
        assert sensor_id == self.expected_id
        self.was_called = True
        return { "itworks": True }

def test_Device_lr_session(monkeypatch):
    _device_data = {"id": 6023}

    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    sked = MockScheduler(6023)
    api._lr_scheduler = sked
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    sess = dev.lr_session()
    assert sess["itworks"]
    assert sked.was_called
    
def test_Device_background_scan(monkeypatch):
    _device_data = {"id": 6023}
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "BACKGROUND_SCAN"
        assert body["device_id"] == [ 6023 ]
        t = body["options"]
        assert t["toggle"] == "ON"
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    dev.background_scan(True)
    assert _was_called
    
def test_Device_bypass(monkeypatch):
    _device_data = {"id": 6023}
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "BYPASS"
        assert body["device_id"] == [ 6023 ]
        t = body["options"]
        assert t["toggle"] == "OFF"
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    dev.bypass(False)
    assert _was_called
    
def test_Device_delete_sensor(monkeypatch):
    _device_data = {"id": 6023}
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "DELETE_SENSOR"
        assert body["device_id"] == [ 6023 ]
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    dev.delete_sensor()
    assert _was_called

def test_Device_uninstall_sensor(monkeypatch):
    _device_data = {"id": 6023}
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "UNINSTALL_SENSOR"
        assert body["device_id"] == [ 6023 ]
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    dev.uninstall_sensor()
    assert _was_called
        
def test_Device_quarantine(monkeypatch):
    _device_data = {"id": 6023}
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "QUARANTINE"
        assert body["device_id"] == [ 6023 ]
        t = body["options"]
        assert t["toggle"] == "ON"
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    dev.quarantine(True)
    assert _was_called

def test_Device_update_policy(monkeypatch):
    _device_data = {"id": 6023}
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "UPDATE_POLICY"
        assert body["device_id"] == [ 6023 ]
        t = body["options"]
        assert t["policy_id"] == 8675309
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    dev.update_policy(8675309)
    assert _was_called

def test_Device_update_sensor_version(monkeypatch):
    _device_data = {"id": 6023}
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _device_data
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        return _device_data
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "UPDATE_SENSOR_VERSION"
        assert body["device_id"] == [ 6023 ]
        t = body["options"]
        t2 = t["sensor_version"]
        assert t2["RHEL"] == "2.3.4.5"
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    dev = Device(api, 6023, _device_data)
    dev.update_sensor_version({"RHEL": "2.3.4.5"})
    assert _was_called
    