import pytest
from cbapi.errors import ApiError
from cbapi.psc.models import Device
from cbapi.psc.rest_api import CbPSCBaseAPI
from test.mocks import ConnectionMocks, MockResponse


def test_get_device(monkeypatch):
    _was_called = False
    
    def mock_get_object(url):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        _was_called = True
        return { "device_id": 6023, "organization_name": "thistestworks" }
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    rc = api.get_device(6023)
    assert _was_called
    assert isinstance(rc, Device)
    assert rc.device_id == 6023
    assert rc.organization_name == "thistestworks"
    
    
def test_device_background_scan(monkeypatch):
    _was_called = False
    
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
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.device_background_scan([ 6023 ], True) 
    assert _was_called
    
    
def test_device_bypass(monkeypatch):
    _was_called = False
    
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
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.device_bypass([ 6023 ], False)
    assert _was_called
    
    
def test_device_delete_sensor(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "DELETE_SENSOR"
        assert body["device_id"] == [ 6023 ]
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.device_delete_sensor([ 6023 ])
    assert _was_called


def test_device_uninstall_sensor(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "UNINSTALL_SENSOR"
        assert body["device_id"] == [ 6023 ]
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.device_uninstall_sensor([ 6023 ])
    assert _was_called
    
    
def test_device_quarantine(monkeypatch):
    _was_called = False
    
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
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.device_quarantine([ 6023 ], True)
    assert _was_called
    
    
def test_device_update_policy(monkeypatch):
    _was_called = False
    
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
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.device_update_policy([ 6023 ], 8675309)
    assert _was_called
    
    
def test_device_update_sensor_version(monkeypatch):
    _was_called = False
    
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
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.device_update_sensor_version([ 6023 ], { "RHEL": "2.3.4.5"})
    assert _was_called
    
    
def test_query_device_with_all_bells_and_whistles(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search"
        assert body["query"] == "foobar"
        t = body.get("criteria", {})
        assert t["ad_group_id"] == [ 14, 25 ]
        assert t["os"] == [ "LINUX" ]
        assert t["policy_id"] == [ 8675309 ]
        assert t["status"] == [ "ALL" ]
        assert t["target_priority"] == [ "HIGH" ]
        t = body.get("exclusions", {})
        assert t["sensor_version"] == [ "0.1" ]
        t = body.get("sort", [])
        t2 = t[0]
        assert t2["field"] == "name"
        assert t2["order"] == "DESC"
        _was_called = True
        body = { "id": 6023, "organization_name": "thistestworks" }
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(Device).where("foobar").ad_group_ids([ 14, 25 ]) \
        .os([ "LINUX" ]).policy_ids([ 8675309 ]).status([ "ALL" ]) \
        .target_priorities(["HIGH"]).exclude_sensor_versions(["0.1"]) \
        .sort_by("name", "DESC")
    d = query.one()
    assert _was_called
    assert d.id == 6023
    assert d.organization_name == "thistestworks"
    
    
def test_query_device_wth_last_contact_time_as_start_end(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search"
        assert body["query"] == "foobar"
        t = body.get("criteria", {})
        t2 = t.get("last_contact_time", {})
        assert t2["start"] == "2019-09-30T12:34:56"
        assert t2["end"] == "2019-10-01T12:00:12"
        _was_called = True
        body = { "id": 6023, "organization_name": "thistestworks" }
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(Device).where("foobar") \
        .last_contact_time(start="2019-09-30T12:34:56", end="2019-10-01T12:00:12")
    d = query.one()
    assert _was_called
    assert d.id == 6023
    assert d.organization_name == "thistestworks"


def test_query_device_with_last_contact_time_as_range(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search"
        assert body["query"] == "foobar"
        t = body.get("criteria", {})
        t2 = t.get("last_contact_time", {})
        assert t2["range"] == "-3w"
        _was_called = True
        body = { "id": 6023, "organization_name": "thistestworks" }
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(Device).where("foobar").last_contact_time(range="-3w")
    d = query.one()
    assert _was_called
    assert d.id == 6023
    assert d.organization_name == "thistestworks"

    
def test_query_device_invalid_ad_group_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).ad_group_ids([ "Bogus" ])
        
        
def test_query_device_invalid_policy_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).policy_ids([ "Bogus" ])
        
        
def test_query_device_last_contact_time_no_params_ok():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).last_contact_time()
            

def test_query_device_last_contact_time_range_specified_bad():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).last_contact_time(start="2019-09-30T12:34:56", \
                                             end="2019-10-01T12:00:12", range="-3w")


def test_query_device_last_contact_time_start_specified_bad():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).last_contact_time(start="2019-09-30T12:34:56", \
                                             range="-3w")


def test_query_device_last_contact_time_end_specified_bad():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).last_contact_time(end="2019-10-01T12:00:12", range="-3w")


def test_query_device_invalid_os():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).os([ "COMMODORE_64" ])
    
    
def test_query_device_invalid_status():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).status([ "Bogus" ])
    
    
def test_query_device_invalid_priority():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).target_priorities([ "Bogus" ])
        
        
def test_query_device_invalid_exclude_sensor_version():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).exclude_sensor_versions([ 12703 ])
        
        
def test_query_device_invalid_sort_direction():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).sort_by("policy_name", "BOGUS")
    
    
def test_query_device_download(monkeypatch):
    _was_called = False
    
    def mock_get_raw_data(url, query_params, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search/download"
        assert query_params["status"] == "ALL"
        assert query_params["ad_group_id"] == "14,25"
        assert query_params["policy_id"] == "8675309"
        assert query_params["target_priority"] == "HIGH"
        assert query_params["query_string"] == "foobar"
        assert query_params["sort_field"] == "name"
        assert query_params["sort_order"] == "DESC"
        _was_called = True
        return "123456789,123456789,123456789"
    
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_raw_data", mock_get_raw_data)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    rc = api.select(Device).where("foobar").ad_group_ids([ 14, 25 ]) \
        .policy_ids([ 8675309 ]).status([ "ALL" ]).target_priorities(["HIGH"]) \
        .sort_by("name", "DESC").download()
    assert _was_called
    assert rc == "123456789,123456789,123456789"
    
    
def test_query_device_do_background_scan(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "BACKGROUND_SCAN"
        t = body["search"]
        assert t["query"] == "foobar"
        t = body["options"]
        assert t["toggle"] == "ON"
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.select(Device).where("foobar").background_scan(True)
    assert _was_called
    
    
def test_query_device_do_bypass(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "BYPASS"
        t = body["search"]
        assert t["query"] == "foobar"
        t = body["options"]
        assert t["toggle"] == "OFF"
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.select(Device).where("foobar").bypass(False)
    assert _was_called


def test_query_device_do_delete_sensor(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "DELETE_SENSOR"
        t = body["search"]
        assert t["query"] == "foobar"
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.select(Device).where("foobar").delete_sensor()
    assert _was_called


def test_query_device_do_uninstall_sensor(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "UNINSTALL_SENSOR"
        t = body["search"]
        assert t["query"] == "foobar"
        _was_called = True
        return MockResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.select(Device).where("foobar").uninstall_sensor()
    assert _was_called
    
    
def test_query_device_do_quarantine(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "QUARANTINE"
        t = body["search"]
        assert t["query"] == "foobar"
        t = body["options"]
        assert t["toggle"] == "ON"
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.select(Device).where("foobar").quarantine(True)
    assert _was_called

    
def test_query_device_do_update_policy(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "UPDATE_POLICY"
        t = body["search"]
        assert t["query"] == "foobar"
        t = body["options"]
        assert t["policy_id"] == 8675309
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.select(Device).where("foobar").update_policy(8675309)
    assert _was_called
    
            
def test_query_device_do_update_sensor_version(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body["action_type"] == "UPDATE_SENSOR_VERSION"
        t = body["search"]
        assert t["query"] == "foobar"
        t = body["options"]
        t2 = t["sensor_version"]
        assert t2["RHEL"] == "2.3.4.5"
        _was_called = True
        return MockResponse(None, 204)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    api.select(Device).where("foobar").update_sensor_version({ "RHEL": "2.3.4.5"})
    assert _was_called

                