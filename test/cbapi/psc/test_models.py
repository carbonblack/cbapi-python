import pytest
from cbapi.psc.models import Device, BaseAlert, WorkflowStatus
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
    
def test_BaseAlert_dismiss(monkeypatch):
    _was_called = False

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/ESD14U2C/workflow"
        assert body["state"] == "DISMISSED"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "Yessir"
        _was_called = True
        return MockResponse({"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                             "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"})
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    alert = BaseAlert(api, "ESD14U2C", {"id": "ESD14U2C", "workflow":{"state": "OPEN"}})
    alert.dismiss("Fixed", "Yessir")
    assert _was_called
    assert alert.workflow_.changed_by == "Robocop"
    assert alert.workflow_.state == "DISMISSED"
    assert alert.workflow_.remediation == "Fixed"
    assert alert.workflow_.comment == "Yessir"
    assert alert.workflow_.last_update_time == "2019-10-31T16:03:13.951Z"

def test_BaseAlert_undismiss(monkeypatch):
    _was_called = False

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/ESD14U2C/workflow"
        assert body["state"] == "OPEN"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "NoSir"
        _was_called = True
        return MockResponse({"state": "OPEN", "remediation": "Fixed", "comment": "NoSir",
                             "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"})
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    alert = BaseAlert(api, "ESD14U2C", {"id": "ESD14U2C", "workflow":{"state": "DISMISS"}})
    alert.update("Fixed", "NoSir")
    assert _was_called
    assert alert.workflow_.changed_by == "Robocop"
    assert alert.workflow_.state == "OPEN"
    assert alert.workflow_.remediation == "Fixed"
    assert alert.workflow_.comment == "NoSir"
    assert alert.workflow_.last_update_time == "2019-10-31T16:03:13.951Z"

def test_BaseAlert_dismiss_threat(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/threat/B0RG/workflow"
        assert body["state"] == "DISMISSED"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "Yessir"
        _was_called = True
        return MockResponse({"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                             "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"})
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    alert = BaseAlert(api, "ESD14U2C", {"id": "ESD14U2C", "threat_id": "B0RG", "workflow":{"state": "OPEN"}})
    wf = alert.dismiss_threat("Fixed", "Yessir")
    assert _was_called
    assert wf.changed_by == "Robocop"
    assert wf.state == "DISMISSED"
    assert wf.remediation == "Fixed"
    assert wf.comment == "Yessir"
    assert wf.last_update_time == "2019-10-31T16:03:13.951Z"

def test_BaseAlert_undismiss_threat(monkeypatch):
    _was_called = False

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/threat/B0RG/workflow"
        assert body["state"] == "OPEN"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "NoSir"
        _was_called = True
        return MockResponse({"state": "OPEN", "remediation": "Fixed", "comment": "NoSir",
                             "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"})
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    alert = BaseAlert(api, "ESD14U2C", {"id": "ESD14U2C", "threat_id": "B0RG", "workflow":{"state": "OPEN"}})
    wf = alert.update_threat("Fixed", "NoSir")
    assert _was_called
    assert wf.changed_by == "Robocop"
    assert wf.state == "OPEN"
    assert wf.remediation == "Fixed"
    assert wf.comment == "NoSir"
    assert wf.last_update_time == "2019-10-31T16:03:13.951Z"
    
def test_WorkflowStatus(monkeypatch):
    _times_called = 0
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _times_called
        assert url == "/appservices/v6/orgs/Z100/workflow/status/W00K13"
        if _times_called >= 0 and _times_called <= 3:
            _stat = "QUEUED"
        elif _times_called >= 4 and _times_called <= 6:
            _stat = "IN_PROGRESS"
        elif _times_called >= 7 and _times_called <= 9:
            _stat = "FINISHED"
        else:
            pytest.fail("mock_get_object called too many times")
        resp = {"errors": [], "failed_ids": [], "id": "W00K13", "num_hits": 0, "num_success": 0, "status": _stat}
        resp["workflow"] = {"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                            "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}
        _times_called = _times_called + 1
        return resp
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    wfstat = WorkflowStatus(api, "W00K13")
    assert wfstat.workflow_.changed_by == "Robocop"
    assert wfstat.workflow_.state == "DISMISSED"
    assert wfstat.workflow_.remediation == "Fixed"
    assert wfstat.workflow_.comment == "Yessir"
    assert wfstat.workflow_.last_update_time == "2019-10-31T16:03:13.951Z"
    assert _times_called == 1
    assert wfstat.queued
    assert not wfstat.in_progress
    assert not wfstat.finished
    assert _times_called == 4
    assert not wfstat.queued
    assert wfstat.in_progress
    assert not wfstat.finished
    assert _times_called == 7
    assert not wfstat.queued
    assert not wfstat.in_progress
    assert wfstat.finished
    assert _times_called == 10
    