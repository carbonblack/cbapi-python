import pytest
from cbapi.errors import ApiError
from cbapi.psc.models import Device, BaseAlert, CBAnalyticsAlert, VMwareAlert, WatchlistAlert
from cbapi.psc.query import BulkUpdateAlerts, BulkUpdateWatchlistAlerts, BulkUpdateThreatAlerts, \
                            BulkUpdateCBAnalyticsAlerts, BulkUpdateVMwareAlerts
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
    rc = api.select(Device, 6023)
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
    
    
def test_query_device_with_last_contact_time_as_start_end(monkeypatch):
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


def test_bulk_query_types_return_ok():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    bquery = api.bulk_alert_dismiss("ALERT")
    assert isinstance(bquery, BulkUpdateAlerts)
    bquery = api.bulk_alert_dismiss("WATCHLIST")
    assert isinstance(bquery, BulkUpdateWatchlistAlerts)
    bquery = api.bulk_alert_dismiss("THREAT")
    assert isinstance(bquery, BulkUpdateThreatAlerts)
    bquery = api.bulk_alert_dismiss("CBANALYTICS")
    assert isinstance(bquery, BulkUpdateCBAnalyticsAlerts)
    bquery = api.bulk_alert_dismiss("VMWARE")
    assert isinstance(bquery, BulkUpdateVMwareAlerts)
    with pytest.raises(ApiError):
        api.bulk_alert_dismiss("CRIMSON")
        
        
def test_query_basealert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_search"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["category"] == ["SERIOUS", "CRITICAL"]
        assert t["device_id"] == [6023]
        assert t["device_name"] == ["HAL"]
        assert t["device_os"] == ["LINUX"]
        assert t["device_os_version"] == ["0.1.2"]
        assert t["device_username"] == ["JRN"]
        assert t.get("group_results", False)
        assert t["id"] == ["S0L0"]
        assert t["legacy_alert_id"] == ["S0L0_1"]
        assert t.get("minimum_severity", -1) == 6
        assert t["policy_id"] == [8675309]
        assert t["policy_name"] == ["Strict"]
        assert t["process_name"] == ["IEXPLORE.EXE"]
        assert t["process_sha256"] == ["0123456789ABCDEF0123456789ABCDEF"]
        assert t["reputation"] == ["SUSPECT_MALWARE"]
        assert t["tag"] == ["Frood"]
        assert t["target_value"] == ["HIGH"]
        assert t["threat_id"] == ["B0RG"]
        assert t["type"] == ["WATCHLIST"]
        assert t["workflow"] == ["OPEN"]
        t = body["sort"]
        t2 = t[0]
        assert t2["field"] == "name"
        assert t2["order"] == "DESC"
        _was_called = True
        body = {"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG", "workflow": {"state": "OPEN"}}
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(BaseAlert).where("Blort").categories(["SERIOUS", "CRITICAL"]).device_ids([6023]) \
        .device_names(["HAL"]).device_os(["LINUX"]).device_os_versions(["0.1.2"]).device_username(["JRN"]) \
        .group_results(True).alert_ids(["S0L0"]).legacy_alert_ids(["S0L0_1"]).minimum_severity(6) \
        .policy_ids([8675309]).policy_names(["Strict"]).process_names(["IEXPLORE.EXE"]) \
        .process_sha256(["0123456789ABCDEF0123456789ABCDEF"]).reputations(["SUSPECT_MALWARE"]) \
        .tags(["Frood"]).target_priorities(["HIGH"]).threat_ids(["B0RG"]).types(["WATCHLIST"]) \
        .workflows(["OPEN"]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_basealert_with_create_time_as_start_end(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_search"
        assert body["query"] == "Blort"
        t = body["criteria"]
        t2 = t.get("create_time", {})
        assert t2["start"] == "2019-09-30T12:34:56"
        assert t2["end"] == "2019-10-01T12:00:12"
        _was_called = True
        body = {"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG", "workflow": {"state": "OPEN"}}
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(BaseAlert).where("Blort") \
        .create_time(start="2019-09-30T12:34:56", end="2019-10-01T12:00:12")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_basealert_with_create_time_as_range(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_search"
        assert body["query"] == "Blort"
        t = body["criteria"]
        t2 = t.get("create_time", {})
        assert t2["range"] == "-3w"
        _was_called = True
        body = {"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG", "workflow": {"state": "OPEN"}}
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(BaseAlert).where("Blort").create_time(range="-3w")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"
    
    
def test_query_basealert_facets(monkeypatch):    
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_facet"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["workflow"] == ["OPEN"]
        t = body["terms"]
        assert t["rows"] == 0
        assert t["fields"] == ["REPUTATION", "STATUS"]
        _was_called = True
        dto1 = {"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]}
        dto2 = {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}
        return MockResponse({"results": [dto1, dto2]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(BaseAlert).where("Blort").workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    t = f[0]
    assert t["values"] == [{"id": "reputation", "name": "reputationX", "total": 4}]
    t = f[1]
    assert t["values"] == [{"id": "status", "name": "statusX", "total": 9}]
    

def test_query_basealert_invalid_category():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).categories(["DOUBLE_DARE"])
        
        
def test_query_basealert_create_time_no_params_ok():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).create_time()


def test_query_basealert_create_time_range_specified_bad():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).create_time(start="2019-09-30T12:34:56", \
                                          end="2019-10-01T12:00:12", range="-3w")
        
        
def test_query_basealert_create_time_start_specified_bad():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).create_time(start="2019-09-30T12:34:56", range="-3w")
        
        
def test_query_basealert_create_time_end_specified_bad():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).create_time(end="2019-10-01T12:00:12", range="-3w")


def test_query_basealert_invalid_device_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).device_ids(["Bogus"])
        
        
def test_query_basealert_invalid_device_names():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).device_names([42])
        
        
def test_query_basealert_invalid_device_os():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).device_os(["TI994A"])
        
        
def test_query_basealert_invalid_device_os_versions():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).device_os_versions([8808])
        
        
def test_query_basealert_invalid_device_username():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).device_username([-1])
        
        
def test_query_basealert_invalid_alert_ids():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).alert_ids([9001])
    
    
def test_query_basealert_invalid_legacy_alert_ids():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).legacy_alert_ids([9001])
    

def test_query_basealert_invalid_policy_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).policy_ids(["Bogus"])
        
        
def test_query_basealert_invalid_policy_names():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).policy_names([323])
        
        
def test_query_basealert_invalid_process_names():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).process_names([7071])
        
        
def test_query_basealert_invalid_process_sha256():        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).process_sha256([123456789])
        
        
def test_query_basealert_invalid_reputations():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).reputations(["MICROSOFT_FUDWARE"])
        
        
def test_query_basealert_invalid_tags():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).tags([990909])
        
        
def test_query_basealert_invalid_target_priorities():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).target_priorities(["DOGWASH"])
        
        
def test_query_basealert_invalid_threat_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).threat_ids([4096])
        
        
def test_query_basealert_invalid_types():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).types(["ERBOSOFT"])
        
        
def test_query_basealert_invalid_workflows():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).workflows(["IN_LIMBO"])
        

def test_query_cbanalyticsalert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/cbanalytics/_search"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["category"] == ["SERIOUS", "CRITICAL"]
        assert t["device_id"] == [6023]
        assert t["device_name"] == ["HAL"]
        assert t["device_os"] == ["LINUX"]
        assert t["device_os_version"] == ["0.1.2"]
        assert t["device_username"] == ["JRN"]
        assert t.get("group_results", False)
        assert t["id"] == ["S0L0"]
        assert t["legacy_alert_id"] == ["S0L0_1"]
        assert t.get("minimum_severity", -1) == 6
        assert t["policy_id"] == [8675309]
        assert t["policy_name"] == ["Strict"]
        assert t["process_name"] == ["IEXPLORE.EXE"]
        assert t["process_sha256"] == ["0123456789ABCDEF0123456789ABCDEF"]
        assert t["reputation"] == ["SUSPECT_MALWARE"]
        assert t["tag"] == ["Frood"]
        assert t["target_value"] == ["HIGH"]
        assert t["threat_id"] == ["B0RG"]
        assert t["type"] == ["WATCHLIST"]
        assert t["workflow"] == ["OPEN"]
        assert t["blocked_threat_category"] == ["RISKY_PROGRAM"]
        assert t["device_location"] == ["ONSITE"]
        assert t["kill_chain_status"] == ["EXECUTE_GOAL"]
        assert t["not_blocked_threat_category"] == ["NEW_MALWARE"]
        assert t["policy_applied"] == ["APPLIED"]
        assert t["reason_code"] == ["ATTACK_VECTOR"]
        assert t["run_state"] == ["RAN"]
        assert t["sensor_action"] == ["DENY"]
        assert t["threat_cause_vector"] == ["WEB"]
        
        t = body["sort"]
        t2 = t[0]
        assert t2["field"] == "name"
        assert t2["order"] == "DESC"
        _was_called = True
        body = {"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG", "workflow": {"state": "OPEN"}}
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(CBAnalyticsAlert).where("Blort").categories(["SERIOUS", "CRITICAL"]).device_ids([6023]) \
        .device_names(["HAL"]).device_os(["LINUX"]).device_os_versions(["0.1.2"]).device_username(["JRN"]) \
        .group_results(True).alert_ids(["S0L0"]).legacy_alert_ids(["S0L0_1"]).minimum_severity(6) \
        .policy_ids([8675309]).policy_names(["Strict"]).process_names(["IEXPLORE.EXE"]) \
        .process_sha256(["0123456789ABCDEF0123456789ABCDEF"]).reputations(["SUSPECT_MALWARE"]) \
        .tags(["Frood"]).target_priorities(["HIGH"]).threat_ids(["B0RG"]).types(["WATCHLIST"]) \
        .workflows(["OPEN"]).blocked_threat_categories(["RISKY_PROGRAM"]).device_locations(["ONSITE"]) \
        .kill_chain_statuses(["EXECUTE_GOAL"]).not_blocked_threat_categories(["NEW_MALWARE"]) \
        .policy_applied(["APPLIED"]).reason_code(["ATTACK_VECTOR"]).run_states(["RAN"]) \
        .sensor_actions(["DENY"]).threat_cause_vectors(["WEB"]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"

        
def test_query_cbanalyticsalert_facets(monkeypatch):    
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/cbanalytics/_facet"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["workflow"] == ["OPEN"]
        t = body["terms"]
        assert t["rows"] == 0
        assert t["fields"] == ["REPUTATION", "STATUS"]
        _was_called = True
        dto1 = {"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]}
        dto2 = {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}
        return MockResponse({"results": [dto1, dto2]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(CBAnalyticsAlert).where("Blort").workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    t = f[0]
    assert t["values"] == [{"id": "reputation", "name": "reputationX", "total": 4}]
    t = f[1]
    assert t["values"] == [{"id": "status", "name": "statusX", "total": 9}]
    

def test_query_cbanalyticsalert_invalid_blocked_threat_categories():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).blocked_threat_categories(["MINOR"])
        

def test_query_cbanalyticsalert_invalid_device_locations():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).device_locations(["NARNIA"])
        
        
def test_query_cbanalyticsalert_invalid_kill_chain_statuses():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).kill_chain_statuses(["SPAWN_COPIES"])


def test_query_cbanalyticsalert_invalid_not_blocked_threat_categories():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).not_blocked_threat_categories(["MINOR"])
    
    
def test_query_cbanalyticsalert_invalid_policy_applied():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).policy_applied(["MAYBE"])
    

def test_query_cbanalyticsalert_invalid_reason_code():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).reason_code([55])
    
    
def test_query_cbanalyticsalert_invalid_run_states():     
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).run_states(["MIGHT_HAVE"])
    
    
def test_query_cbanalyticsalert_invalid_sensor_actions():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).sensor_actions(["FLIP_A_COIN"])


def test_query_cbanalyticsalert_invalid_threat_cause_vectors():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(CBAnalyticsAlert).threat_cause_vectors(["NETWORK"])
              
              
def test_query_vmwarealert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/vmware/_search"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["category"] == ["SERIOUS", "CRITICAL"]
        assert t["device_id"] == [6023]
        assert t["device_name"] == ["HAL"]
        assert t["device_os"] == ["LINUX"]
        assert t["device_os_version"] == ["0.1.2"]
        assert t["device_username"] == ["JRN"]
        assert t.get("group_results", False)
        assert t["id"] == ["S0L0"]
        assert t["legacy_alert_id"] == ["S0L0_1"]
        assert t.get("minimum_severity", -1) == 6
        assert t["policy_id"] == [8675309]
        assert t["policy_name"] == ["Strict"]
        assert t["process_name"] == ["IEXPLORE.EXE"]
        assert t["process_sha256"] == ["0123456789ABCDEF0123456789ABCDEF"]
        assert t["reputation"] == ["SUSPECT_MALWARE"]
        assert t["tag"] == ["Frood"]
        assert t["target_value"] == ["HIGH"]
        assert t["threat_id"] == ["B0RG"]
        assert t["type"] == ["WATCHLIST"]
        assert t["workflow"] == ["OPEN"]
        assert t["group_id"] == [14]
        t = body["sort"]
        t2 = t[0]
        assert t2["field"] == "name"
        assert t2["order"] == "DESC"
        _was_called = True
        body = {"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG", "workflow": {"state": "OPEN"}}
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(VMwareAlert).where("Blort").categories(["SERIOUS", "CRITICAL"]).device_ids([6023]) \
        .device_names(["HAL"]).device_os(["LINUX"]).device_os_versions(["0.1.2"]).device_username(["JRN"]) \
        .group_results(True).alert_ids(["S0L0"]).legacy_alert_ids(["S0L0_1"]).minimum_severity(6) \
        .policy_ids([8675309]).policy_names(["Strict"]).process_names(["IEXPLORE.EXE"]) \
        .process_sha256(["0123456789ABCDEF0123456789ABCDEF"]).reputations(["SUSPECT_MALWARE"]) \
        .tags(["Frood"]).target_priorities(["HIGH"]).threat_ids(["B0RG"]).types(["WATCHLIST"]) \
        .workflows(["OPEN"]).group_ids([14]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"
              
              
def test_query_vmwarealert_facets(monkeypatch):    
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/vmware/_facet"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["workflow"] == ["OPEN"]
        t = body["terms"]
        assert t["rows"] == 0
        assert t["fields"] == ["REPUTATION", "STATUS"]
        _was_called = True
        dto1 = {"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]}
        dto2 = {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}
        return MockResponse({"results": [dto1, dto2]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(VMwareAlert).where("Blort").workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    t = f[0]
    assert t["values"] == [{"id": "reputation", "name": "reputationX", "total": 4}]
    t = f[1]
    assert t["values"] == [{"id": "status", "name": "statusX", "total": 9}]
    

def test_query_vmwarealert_invalid_group_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(VMwareAlert).group_ids(["Bogus"])
        
        
def test_query_watchlistalert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/watchlist/_search"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["category"] == ["SERIOUS", "CRITICAL"]
        assert t["device_id"] == [6023]
        assert t["device_name"] == ["HAL"]
        assert t["device_os"] == ["LINUX"]
        assert t["device_os_version"] == ["0.1.2"]
        assert t["device_username"] == ["JRN"]
        assert t.get("group_results", False)
        assert t["id"] == ["S0L0"]
        assert t["legacy_alert_id"] == ["S0L0_1"]
        assert t.get("minimum_severity", -1) == 6
        assert t["policy_id"] == [8675309]
        assert t["policy_name"] == ["Strict"]
        assert t["process_name"] == ["IEXPLORE.EXE"]
        assert t["process_sha256"] == ["0123456789ABCDEF0123456789ABCDEF"]
        assert t["reputation"] == ["SUSPECT_MALWARE"]
        assert t["tag"] == ["Frood"]
        assert t["target_value"] == ["HIGH"]
        assert t["threat_id"] == ["B0RG"]
        assert t["type"] == ["WATCHLIST"]
        assert t["workflow"] == ["OPEN"]
        assert t["watchlist_id"] == ["100"]
        assert t["watchlist_name"] == ["Gandalf"]
        t = body["sort"]
        t2 = t[0]
        assert t2["field"] == "name"
        assert t2["order"] == "DESC"
        _was_called = True
        body = {"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG", "workflow": {"state": "OPEN"}}
        envelope = { "results": [ body ], "num_found": 1 }
        return MockResponse(envelope)
        
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(WatchlistAlert).where("Blort").categories(["SERIOUS", "CRITICAL"]).device_ids([6023]) \
        .device_names(["HAL"]).device_os(["LINUX"]).device_os_versions(["0.1.2"]).device_username(["JRN"]) \
        .group_results(True).alert_ids(["S0L0"]).legacy_alert_ids(["S0L0_1"]).minimum_severity(6) \
        .policy_ids([8675309]).policy_names(["Strict"]).process_names(["IEXPLORE.EXE"]) \
        .process_sha256(["0123456789ABCDEF0123456789ABCDEF"]).reputations(["SUSPECT_MALWARE"]) \
        .tags(["Frood"]).target_priorities(["HIGH"]).threat_ids(["B0RG"]).types(["WATCHLIST"]) \
        .workflows(["OPEN"]).watchlist_ids(["100"]).watchlist_names(["Gandalf"]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"
        
        
def test_query_watchlistalert_facets(monkeypatch):    
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/watchlist/_facet"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["workflow"] == ["OPEN"]
        t = body["terms"]
        assert t["rows"] == 0
        assert t["fields"] == ["REPUTATION", "STATUS"]
        _was_called = True
        dto1 = {"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]}
        dto2 = {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}
        return MockResponse({"results": [dto1, dto2]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.select(WatchlistAlert).where("Blort").workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    t = f[0]
    assert t["values"] == [{"id": "reputation", "name": "reputationX", "total": 4}]
    t = f[1]
    assert t["values"] == [{"id": "status", "name": "statusX", "total": 9}]
    

def test_query_watchlistalert_invalid_watchlist_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(WatchlistAlert).watchlist_ids([888])
        
        
def test_query_watchlistalert_invalid_watchlist_names():         
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(WatchlistAlert).watchlist_names([69])
    
    
def test_alerts_bulk_dismiss(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/workflow/_criteria"
        assert body["query"] == "Blort"
        assert body["state"] == "DISMISSED"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "Yessir"
        t = body["criteria"]
        assert t["device_name"] == ["HAL9000"]
        _was_called = True
        return MockResponse({"request_id": "497ABX"})
    
    def mock_get_object(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/workflow/status/497ABX"
        resp = {"errors": [], "failed_ids": [], "id": "497ABX", "num_hits": 0, "num_success": 0, "status": "QUEUED"}
        resp["workflow"] = {"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                            "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}
        return resp
      
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    q = api.bulk_alert_dismiss("ALERT").remediation("Fixed").comment("Yessir")
    wstat = q.where("Blort").device_names(["HAL9000"]).run()
    assert _was_called
    assert wstat.id_ == "497ABX"


def test_alerts_bulk_undismiss(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/workflow/_criteria"
        assert body["query"] == "Blort"
        assert body["state"] == "OPEN"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "NoSir"
        t = body["criteria"]
        assert t["device_name"] == ["HAL9000"]
        _was_called = True
        return MockResponse({"request_id": "497ABX"})
    
    def mock_get_object(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/workflow/status/497ABX"
        resp = {"errors": [], "failed_ids": [], "id": "497ABX", "num_hits": 0, "num_success": 0, "status": "QUEUED"}
        resp["workflow"] = {"state": "OPEN", "remediation": "Fixed", "comment": "NoSir",
                            "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}
        return resp
      
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    q = api.bulk_alert_undismiss("ALERT").remediation("Fixed").comment("NoSir")
    wstat = q.where("Blort").device_names(["HAL9000"]).run()
    assert _was_called
    assert wstat.id_ == "497ABX"
        
        
def test_alerts_bulk_dismiss_watchlist(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/watchlist/workflow/_criteria"
        assert body["query"] == "Blort"
        assert body["state"] == "DISMISSED"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "Yessir"
        t = body["criteria"]
        assert t["device_name"] == ["HAL9000"]
        _was_called = True
        return MockResponse({"request_id": "497ABX"})
    
    def mock_get_object(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/workflow/status/497ABX"
        resp = {"errors": [], "failed_ids": [], "id": "497ABX", "num_hits": 0, "num_success": 0, "status": "QUEUED"}
        resp["workflow"] = {"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                            "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}
        return resp
      
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    q = api.bulk_alert_dismiss("WATCHLIST").remediation("Fixed").comment("Yessir")
    wstat = q.where("Blort").device_names(["HAL9000"]).run()
    assert _was_called
    assert wstat.id_ == "497ABX"


def test_alerts_bulk_dismiss_cbanalytics(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/cbanalytics/workflow/_criteria"
        assert body["query"] == "Blort"
        assert body["state"] == "DISMISSED"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "Yessir"
        t = body["criteria"]
        assert t["device_name"] == ["HAL9000"]
        _was_called = True
        return MockResponse({"request_id": "497ABX"})
    
    def mock_get_object(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/workflow/status/497ABX"
        resp = {"errors": [], "failed_ids": [], "id": "497ABX", "num_hits": 0, "num_success": 0, "status": "QUEUED"}
        resp["workflow"] = {"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                            "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}
        return resp
      
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    q = api.bulk_alert_dismiss("CBANALYTICS").remediation("Fixed").comment("Yessir")
    wstat = q.where("Blort").device_names(["HAL9000"]).run()
    assert _was_called
    assert wstat.id_ == "497ABX"


def test_alerts_bulk_dismiss_vmware(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/vmware/workflow/_criteria"
        assert body["query"] == "Blort"
        assert body["state"] == "DISMISSED"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "Yessir"
        t = body["criteria"]
        assert t["device_name"] == ["HAL9000"]
        _was_called = True
        return MockResponse({"request_id": "497ABX"})
    
    def mock_get_object(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/workflow/status/497ABX"
        resp = {"errors": [], "failed_ids": [], "id": "497ABX", "num_hits": 0, "num_success": 0, "status": "QUEUED"}
        resp["workflow"] = {"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                            "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}
        return resp
      
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    q = api.bulk_alert_dismiss("VMWARE").remediation("Fixed").comment("Yessir")
    wstat = q.where("Blort").device_names(["HAL9000"]).run()
    assert _was_called
    assert wstat.id_ == "497ABX"


def test_alerts_bulk_dismiss_threat(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/threat/workflow/_criteria"
        assert body["threat_id"] == ["B0RG", "F3R3NG1"]
        assert body["state"] == "DISMISSED"
        assert body["remediation_state"] == "Fixed"
        assert body["comment"] == "Yessir"
        _was_called = True
        return MockResponse({"request_id": "497ABX"})
        
    def mock_get_object(url, parms=None, default=None):
        assert url == "/appservices/v6/orgs/Z100/workflow/status/497ABX"
        resp = {"errors": [], "failed_ids": [], "id": "497ABX", "num_hits": 0, "num_success": 0, "status": "QUEUED"}
        resp["workflow"] = {"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                            "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}
        return resp
      
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    q = api.bulk_alert_dismiss("THREAT").remediation("Fixed").comment("Yessir")
    wstat = q.threat_ids(["B0RG", "F3R3NG1"]).run()
    assert _was_called
    assert wstat.id_ == "497ABX"
