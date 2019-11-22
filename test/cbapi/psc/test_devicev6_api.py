import pytest
from cbapi.errors import ApiError
from cbapi.psc.models import Device
from cbapi.psc.rest_api import CbPSCBaseAPI
from test.cbtest import StubResponse, patch_cbapi


def test_get_device(monkeypatch):
    _was_called = False

    def _get_device(url):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/6023"
        _was_called = True
        return {"device_id": 6023, "organization_name": "thistestworks"}

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_device)
    rc = api.select(Device, 6023)
    assert _was_called
    assert isinstance(rc, Device)
    assert rc.device_id == 6023
    assert rc.organization_name == "thistestworks"


def test_device_background_scan(monkeypatch):
    _was_called = False

    def _call_background_scan(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "BACKGROUND_SCAN", "device_id": [6023], "options": {"toggle": "ON"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_call_background_scan)
    api.device_background_scan([6023], True)
    assert _was_called


def test_device_bypass(monkeypatch):
    _was_called = False

    def _call_bypass(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "BYPASS", "device_id": [6023], "options": {"toggle": "OFF"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_call_bypass)
    api.device_bypass([6023], False)
    assert _was_called


def test_device_delete_sensor(monkeypatch):
    _was_called = False

    def _call_delete_sensor(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "DELETE_SENSOR", "device_id": [6023]}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_call_delete_sensor)
    api.device_delete_sensor([6023])
    assert _was_called


def test_device_uninstall_sensor(monkeypatch):
    _was_called = False

    def _call_uninstall_sensor(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UNINSTALL_SENSOR", "device_id": [6023]}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_call_uninstall_sensor)
    api.device_uninstall_sensor([6023])
    assert _was_called


def test_device_quarantine(monkeypatch):
    _was_called = False

    def _call_quarantine(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "QUARANTINE", "device_id": [6023], "options": {"toggle": "ON"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_call_quarantine)
    api.device_quarantine([6023], True)
    assert _was_called


def test_device_update_policy(monkeypatch):
    _was_called = False

    def _call_update_policy(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UPDATE_POLICY", "device_id": [6023], "options": {"policy_id": 8675309}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_call_update_policy)
    api.device_update_policy([6023], 8675309)
    assert _was_called


def test_device_update_sensor_version(monkeypatch):
    _was_called = False

    def _call_update_sensor_version(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UPDATE_SENSOR_VERSION", "device_id": [6023],
                        "options": {"sensor_version": {"RHEL": "2.3.4.5"}}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_call_update_sensor_version)
    api.device_update_sensor_version([6023], {"RHEL": "2.3.4.5"})
    assert _was_called


def test_query_device_with_all_bells_and_whistles(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search"
        assert body == {"query": "foobar",
                        "criteria": {"ad_group_id": [14, 25], "os": ["LINUX"], "policy_id": [8675309],
                                     "status": ["ALL"], "target_priority": ["HIGH"]},
                        "exclusions": {"sensor_version": ["0.1"]},
                        "sort": [{"field": "name", "order": "DESC"}]}
        _was_called = True
        return StubResponse({"results": [{"id": 6023, "organization_name": "thistestworks"}],
                             "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(Device).where("foobar").set_ad_group_ids([14, 25]).set_os(["LINUX"]) \
        .set_policy_ids([8675309]).set_status(["ALL"]).set_target_priorities(["HIGH"]) \
        .set_exclude_sensor_versions(["0.1"]).sort_by("name", "DESC")
    d = query.one()
    assert _was_called
    assert d.id == 6023
    assert d.organization_name == "thistestworks"


def test_query_device_with_last_contact_time_as_start_end(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search"
        assert body == {"query": "foobar",
                        "criteria": {"last_contact_time": {"start": "2019-09-30T12:34:56",
                                                           "end": "2019-10-01T12:00:12"}}, "exclusions": {}}
        _was_called = True
        return StubResponse({"results": [{"id": 6023, "organization_name": "thistestworks"}],
                             "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(Device).where("foobar") \
        .set_last_contact_time(start="2019-09-30T12:34:56", end="2019-10-01T12:00:12")
    d = query.one()
    assert _was_called
    assert d.id == 6023
    assert d.organization_name == "thistestworks"


def test_query_device_with_last_contact_time_as_range(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search"
        assert body == {"query": "foobar", "criteria": {"last_contact_time": {"range": "-3w"}}, "exclusions": {}}
        _was_called = True
        return StubResponse({"results": [{"id": 6023, "organization_name": "thistestworks"}],
                             "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(Device).where("foobar").set_last_contact_time(range="-3w")
    d = query.one()
    assert _was_called
    assert d.id == 6023
    assert d.organization_name == "thistestworks"


def test_query_device_invalid_last_contact_time_combinations():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).set_last_contact_time()
    with pytest.raises(ApiError):
        api.select(Device).set_last_contact_time(start="2019-09-30T12:34:56", end="2019-10-01T12:00:12",
                                                 range="-3w")
    with pytest.raises(ApiError):
        api.select(Device).set_last_contact_time(start="2019-09-30T12:34:56", range="-3w")
    with pytest.raises(ApiError):
        api.select(Device).set_last_contact_time(end="2019-10-01T12:00:12", range="-3w")


def test_query_device_invalid_criteria_values():
    tests = [
        {"method": "set_ad_group_ids", "arg": ["Bogus"]},
        {"method": "set_policy_ids", "arg": ["Bogus"]},
        {"method": "set_os", "arg": ["COMMODORE_64"]},
        {"method": "set_status", "arg": ["Bogus"]},
        {"method": "set_target_priorities", "arg": ["Bogus"]},
        {"method": "set_exclude_sensor_versions", "arg": [12703]}
        ]
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    query = api.select(Device)
    for t in tests:
        meth = getattr(query, t["method"], None)
        with pytest.raises(ApiError):
            meth(t["arg"])


def test_query_device_invalid_sort_direction():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(Device).sort_by("policy_name", "BOGUS")


def test_query_device_download(monkeypatch):
    _was_called = False

    def _run_download(url, query_params, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/devices/_search/download"
        assert query_params == {"status": "ALL", "ad_group_id": "14,25", "policy_id": "8675309",
                                "target_priority": "HIGH", "query_string": "foobar", "sort_field": "name",
                                "sort_order": "DESC"}
        _was_called = True
        return "123456789,123456789,123456789"

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, RAW_GET=_run_download)
    rc = api.select(Device).where("foobar").set_ad_group_ids([14, 25]).set_policy_ids([8675309]) \
        .set_status(["ALL"]).set_target_priorities(["HIGH"]).sort_by("name", "DESC").download()
    assert _was_called
    assert rc == "123456789,123456789,123456789"


def test_query_device_do_background_scan(monkeypatch):
    _was_called = False

    def _background_scan(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "BACKGROUND_SCAN",
                        "search": {"query": "foobar", "criteria": {}, "exclusions": {}}, "options": {"toggle": "ON"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_background_scan)
    api.select(Device).where("foobar").background_scan(True)
    assert _was_called


def test_query_device_do_bypass(monkeypatch):
    _was_called = False

    def _bypass(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "BYPASS",
                        "search": {"query": "foobar", "criteria": {}, "exclusions": {}}, "options": {"toggle": "OFF"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_bypass)
    api.select(Device).where("foobar").bypass(False)
    assert _was_called


def test_query_device_do_delete_sensor(monkeypatch):
    _was_called = False

    def _delete_sensor(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "DELETE_SENSOR",
                        "search": {"query": "foobar", "criteria": {}, "exclusions": {}}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_delete_sensor)
    api.select(Device).where("foobar").delete_sensor()
    assert _was_called


def test_query_device_do_uninstall_sensor(monkeypatch):
    _was_called = False

    def _uninstall_sensor(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UNINSTALL_SENSOR",
                        "search": {"query": "foobar", "criteria": {}, "exclusions": {}}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_uninstall_sensor)
    api.select(Device).where("foobar").uninstall_sensor()
    assert _was_called


def test_query_device_do_quarantine(monkeypatch):
    _was_called = False

    def _quarantine(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "QUARANTINE",
                        "search": {"query": "foobar", "criteria": {}, "exclusions": {}}, "options": {"toggle": "ON"}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_quarantine)
    api.select(Device).where("foobar").quarantine(True)
    assert _was_called


def test_query_device_do_update_policy(monkeypatch):
    _was_called = False

    def _update_policy(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UPDATE_POLICY",
                        "search": {"query": "foobar", "criteria": {}, "exclusions": {}},
                        "options": {"policy_id": 8675309}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_update_policy)
    api.select(Device).where("foobar").update_policy(8675309)
    assert _was_called


def test_query_device_do_update_sensor_version(monkeypatch):
    _was_called = False

    def _update_sensor_version(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/device_actions"
        assert body == {"action_type": "UPDATE_SENSOR_VERSION",
                        "search": {"query": "foobar", "criteria": {}, "exclusions": {}},
                        "options": {"sensor_version": {"RHEL": "2.3.4.5"}}}
        _was_called = True
        return StubResponse(None, 204)

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_update_sensor_version)
    api.select(Device).where("foobar").update_sensor_version({"RHEL": "2.3.4.5"})
    assert _was_called
