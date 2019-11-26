import pytest
from cbapi.errors import ApiError
from cbapi.psc.models import BaseAlert, CBAnalyticsAlert, VMwareAlert, WatchlistAlert, WorkflowStatus
from cbapi.psc.rest_api import CbPSCBaseAPI
from test.cbtest import StubResponse, patch_cbapi


def test_query_basealert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_search"
        assert body == {"query": "Blort",
                        "criteria": {"category": ["SERIOUS", "CRITICAL"], "device_id": [6023], "device_name": ["HAL"],
                                     "device_os": ["LINUX"], "device_os_version": ["0.1.2"],
                                     "device_username": ["JRN"], "group_results": True, "id": ["S0L0"],
                                     "legacy_alert_id": ["S0L0_1"], "minimum_severity": 6, "policy_id": [8675309],
                                     "policy_name": ["Strict"], "process_name": ["IEXPLORE.EXE"],
                                     "process_sha256": ["0123456789ABCDEF0123456789ABCDEF"],
                                     "reputation": ["SUSPECT_MALWARE"], "tag": ["Frood"], "target_value": ["HIGH"],
                                     "threat_id": ["B0RG"], "type": ["WATCHLIST"], "workflow": ["OPEN"]},
                        "sort": [{"field": "name", "order": "DESC"}]}
        _was_called = True
        return StubResponse({"results": [{"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG",
                                          "workflow": {"state": "OPEN"}}], "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(BaseAlert).where("Blort").set_categories(["SERIOUS", "CRITICAL"]).set_device_ids([6023]) \
        .set_device_names(["HAL"]).set_device_os(["LINUX"]).set_device_os_versions(["0.1.2"]) \
        .set_device_username(["JRN"]).set_group_results(True).set_alert_ids(["S0L0"]) \
        .set_legacy_alert_ids(["S0L0_1"]).set_minimum_severity(6).set_policy_ids([8675309]) \
        .set_policy_names(["Strict"]).set_process_names(["IEXPLORE.EXE"]) \
        .set_process_sha256(["0123456789ABCDEF0123456789ABCDEF"]).set_reputations(["SUSPECT_MALWARE"]) \
        .set_tags(["Frood"]).set_target_priorities(["HIGH"]).set_threat_ids(["B0RG"]).set_types(["WATCHLIST"]) \
        .set_workflows(["OPEN"]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_basealert_with_create_time_as_start_end(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_search"
        assert body == {"query": "Blort",
                        "criteria": {"create_time": {"start": "2019-09-30T12:34:56", "end": "2019-10-01T12:00:12"}}}
        _was_called = True
        return StubResponse({"results": [{"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG",
                                          "workflow": {"state": "OPEN"}}], "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(BaseAlert).where("Blort").set_create_time(start="2019-09-30T12:34:56",
                                                                 end="2019-10-01T12:00:12")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_basealert_with_create_time_as_range(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_search"
        assert body == {"query": "Blort", "criteria": {"create_time": {"range": "-3w"}}}
        _was_called = True
        return StubResponse({"results": [{"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG",
                                          "workflow": {"state": "OPEN"}}], "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(BaseAlert).where("Blort").set_create_time(range="-3w")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_basealert_facets(monkeypatch):
    _was_called = False

    def _run_facet_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/_facet"
        assert body["query"] == "Blort"
        t = body["criteria"]
        assert t["workflow"] == ["OPEN"]
        t = body["terms"]
        assert t["rows"] == 0
        assert t["fields"] == ["REPUTATION", "STATUS"]
        _was_called = True
        return StubResponse({"results": [{"field": {},
                                          "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                                         {"field": {},
                                          "values": [{"id": "status", "name": "statusX", "total": 9}]}]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_facet_query)
    query = api.select(BaseAlert).where("Blort").set_workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    assert f == [{"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                 {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}]


def test_query_basealert_invalid_create_time_combinations():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(BaseAlert).set_create_time()
    with pytest.raises(ApiError):
        api.select(BaseAlert).set_create_time(start="2019-09-30T12:34:56",
                                              end="2019-10-01T12:00:12", range="-3w")
    with pytest.raises(ApiError):
        api.select(BaseAlert).set_create_time(start="2019-09-30T12:34:56", range="-3w")
    with pytest.raises(ApiError):
        api.select(BaseAlert).set_create_time(end="2019-10-01T12:00:12", range="-3w")


def test_query_basealert_invalid_criteria_values():
    tests = [
        {"method": "set_categories", "arg": ["DOUBLE_DARE"]},
        {"method": "set_device_ids", "arg": ["Bogus"]},
        {"method": "set_device_names", "arg": [42]},
        {"method": "set_device_os", "arg": ["TI994A"]},
        {"method": "set_device_os_versions", "arg": [8808]},
        {"method": "set_device_username", "arg": [-1]},
        {"method": "set_alert_ids", "arg": [9001]},
        {"method": "set_legacy_alert_ids", "arg": [9001]},
        {"method": "set_policy_ids", "arg": ["Bogus"]},
        {"method": "set_policy_names", "arg": [323]},
        {"method": "set_process_names", "arg": [7071]},
        {"method": "set_process_sha256", "arg": [123456789]},
        {"method": "set_reputations", "arg": ["MICROSOFT_FUDWARE"]},
        {"method": "set_tags", "arg": [-1]},
        {"method": "set_target_priorities", "arg": ["DOGWASH"]},
        {"method": "set_threat_ids", "arg": [4096]},
        {"method": "set_types", "arg": ["ERBOSOFT"]},
        {"method": "set_workflows", "arg": ["IN_LIMBO"]},
        ]
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    query = api.select(BaseAlert)
    for t in tests:
        meth = getattr(query, t["method"], None)
        with pytest.raises(ApiError):
            meth(t["arg"])


def test_query_cbanalyticsalert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/cbanalytics/_search"
        assert body == {"query": "Blort",
                        "criteria": {"category": ["SERIOUS", "CRITICAL"], "device_id": [6023], "device_name": ["HAL"],
                                     "device_os": ["LINUX"], "device_os_version": ["0.1.2"],
                                     "device_username": ["JRN"], "group_results": True, "id": ["S0L0"],
                                     "legacy_alert_id": ["S0L0_1"], "minimum_severity": 6, "policy_id": [8675309],
                                     "policy_name": ["Strict"], "process_name": ["IEXPLORE.EXE"],
                                     "process_sha256": ["0123456789ABCDEF0123456789ABCDEF"],
                                     "reputation": ["SUSPECT_MALWARE"], "tag": ["Frood"], "target_value": ["HIGH"],
                                     "threat_id": ["B0RG"], "type": ["WATCHLIST"], "workflow": ["OPEN"],
                                     "blocked_threat_category": ["RISKY_PROGRAM"], "device_location": ["ONSITE"],
                                     "kill_chain_status": ["EXECUTE_GOAL"],
                                     "not_blocked_threat_category": ["NEW_MALWARE"], "policy_applied": ["APPLIED"],
                                     "reason_code": ["ATTACK_VECTOR"], "run_state": ["RAN"], "sensor_action": ["DENY"],
                                     "threat_cause_vector": ["WEB"]}, "sort": [{"field": "name", "order": "DESC"}]}
        _was_called = True
        return StubResponse({"results": [{"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG",
                                          "workflow": {"state": "OPEN"}}], "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(CBAnalyticsAlert).where("Blort").set_categories(["SERIOUS", "CRITICAL"]) \
        .set_device_ids([6023]).set_device_names(["HAL"]).set_device_os(["LINUX"]).set_device_os_versions(["0.1.2"]) \
        .set_device_username(["JRN"]).set_group_results(True).set_alert_ids(["S0L0"]).set_legacy_alert_ids(["S0L0_1"]) \
        .set_minimum_severity(6).set_policy_ids([8675309]).set_policy_names(["Strict"]) \
        .set_process_names(["IEXPLORE.EXE"]).set_process_sha256(["0123456789ABCDEF0123456789ABCDEF"]) \
        .set_reputations(["SUSPECT_MALWARE"]).set_tags(["Frood"]).set_target_priorities(["HIGH"]) \
        .set_threat_ids(["B0RG"]).set_types(["WATCHLIST"]).set_workflows(["OPEN"]) \
        .set_blocked_threat_categories(["RISKY_PROGRAM"]).set_device_locations(["ONSITE"]) \
        .set_kill_chain_statuses(["EXECUTE_GOAL"]).set_not_blocked_threat_categories(["NEW_MALWARE"]) \
        .set_policy_applied(["APPLIED"]).set_reason_code(["ATTACK_VECTOR"]).set_run_states(["RAN"]) \
        .set_sensor_actions(["DENY"]).set_threat_cause_vectors(["WEB"]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_cbanalyticsalert_facets(monkeypatch):
    _was_called = False

    def _run_facet_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/cbanalytics/_facet"
        assert body == {"query": "Blort", "criteria": {"workflow": ["OPEN"]},
                        "terms": {"rows": 0, "fields": ["REPUTATION", "STATUS"]}}
        _was_called = True
        return StubResponse({"results": [{"field": {},
                                          "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                                         {"field": {},
                                          "values": [{"id": "status", "name": "statusX", "total": 9}]}]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_facet_query)
    query = api.select(CBAnalyticsAlert).where("Blort").set_workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    assert f == [{"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                 {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}]


def test_query_cbanalyticsalert_invalid_criteria_values():
    tests = [
        {"method": "set_blocked_threat_categories", "arg": ["MINOR"]},
        {"method": "set_device_locations", "arg": ["NARNIA"]},
        {"method": "set_kill_chain_statuses", "arg": ["SPAWN_COPIES"]},
        {"method": "set_not_blocked_threat_categories", "arg": ["MINOR"]},
        {"method": "set_policy_applied", "arg": ["MAYBE"]},
        {"method": "set_reason_code", "arg": [55]},
        {"method": "set_run_states", "arg": ["MIGHT_HAVE"]},
        {"method": "set_sensor_actions", "arg": ["FLIP_A_COIN"]},
        {"method": "set_threat_cause_vectors", "arg": ["NETWORK"]}
        ]
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    query = api.select(CBAnalyticsAlert)
    for t in tests:
        meth = getattr(query, t["method"], None)
        with pytest.raises(ApiError):
            meth(t["arg"])


def test_query_vmwarealert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/vmware/_search"
        assert body == {"query": "Blort",
                        "criteria": {"category": ["SERIOUS", "CRITICAL"], "device_id": [6023], "device_name": ["HAL"],
                                     "device_os": ["LINUX"], "device_os_version": ["0.1.2"],
                                     "device_username": ["JRN"], "group_results": True, "id": ["S0L0"],
                                     "legacy_alert_id": ["S0L0_1"], "minimum_severity": 6, "policy_id": [8675309],
                                     "policy_name": ["Strict"], "process_name": ["IEXPLORE.EXE"],
                                     "process_sha256": ["0123456789ABCDEF0123456789ABCDEF"],
                                     "reputation": ["SUSPECT_MALWARE"], "tag": ["Frood"], "target_value": ["HIGH"],
                                     "threat_id": ["B0RG"], "type": ["WATCHLIST"], "workflow": ["OPEN"],
                                     "group_id": [14]}, "sort": [{"field": "name", "order": "DESC"}]}
        _was_called = True
        return StubResponse({"results": [{"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG",
                                          "workflow": {"state": "OPEN"}}], "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(VMwareAlert).where("Blort").set_categories(["SERIOUS", "CRITICAL"]).set_device_ids([6023]) \
        .set_device_names(["HAL"]).set_device_os(["LINUX"]).set_device_os_versions(["0.1.2"]) \
        .set_device_username(["JRN"]).set_group_results(True).set_alert_ids(["S0L0"]) \
        .set_legacy_alert_ids(["S0L0_1"]).set_minimum_severity(6).set_policy_ids([8675309]) \
        .set_policy_names(["Strict"]).set_process_names(["IEXPLORE.EXE"]) \
        .set_process_sha256(["0123456789ABCDEF0123456789ABCDEF"]).set_reputations(["SUSPECT_MALWARE"]) \
        .set_tags(["Frood"]).set_target_priorities(["HIGH"]).set_threat_ids(["B0RG"]).set_types(["WATCHLIST"]) \
        .set_workflows(["OPEN"]).set_group_ids([14]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_vmwarealert_facets(monkeypatch):
    _was_called = False

    def _run_facet_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/vmware/_facet"
        assert body == {"query": "Blort", "criteria": {"workflow": ["OPEN"]},
                        "terms": {"rows": 0, "fields": ["REPUTATION", "STATUS"]}}
        _was_called = True
        return StubResponse({"results": [{"field": {},
                                          "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                                         {"field": {},
                                          "values": [{"id": "status", "name": "statusX", "total": 9}]}]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_facet_query)
    query = api.select(VMwareAlert).where("Blort").set_workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    assert f == [{"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                 {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}]


def test_query_vmwarealert_invalid_group_ids():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(VMwareAlert).set_group_ids(["Bogus"])


def test_query_watchlistalert_with_all_bells_and_whistles(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/watchlist/_search"
        assert body == {"query": "Blort",
                        "criteria": {"category": ["SERIOUS", "CRITICAL"], "device_id": [6023], "device_name": ["HAL"],
                                     "device_os": ["LINUX"], "device_os_version": ["0.1.2"],
                                     "device_username": ["JRN"], "group_results": True, "id": ["S0L0"],
                                     "legacy_alert_id": ["S0L0_1"], "minimum_severity": 6, "policy_id": [8675309],
                                     "policy_name": ["Strict"], "process_name": ["IEXPLORE.EXE"],
                                     "process_sha256": ["0123456789ABCDEF0123456789ABCDEF"],
                                     "reputation": ["SUSPECT_MALWARE"], "tag": ["Frood"], "target_value": ["HIGH"],
                                     "threat_id": ["B0RG"], "type": ["WATCHLIST"], "workflow": ["OPEN"],
                                     "watchlist_id": ["100"], "watchlist_name": ["Gandalf"]},
                        "sort": [{"field": "name", "order": "DESC"}]}
        _was_called = True
        return StubResponse({"results": [{"id": "S0L0", "org_key": "Z100", "threat_id": "B0RG",
                                          "workflow": {"state": "OPEN"}}], "num_found": 1})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.select(WatchlistAlert).where("Blort").set_categories(["SERIOUS", "CRITICAL"]).set_device_ids([6023]) \
        .set_device_names(["HAL"]).set_device_os(["LINUX"]).set_device_os_versions(["0.1.2"]) \
        .set_device_username(["JRN"]).set_group_results(True).set_alert_ids(["S0L0"]) \
        .set_legacy_alert_ids(["S0L0_1"]).set_minimum_severity(6).set_policy_ids([8675309]) \
        .set_policy_names(["Strict"]).set_process_names(["IEXPLORE.EXE"]) \
        .set_process_sha256(["0123456789ABCDEF0123456789ABCDEF"]).set_reputations(["SUSPECT_MALWARE"]) \
        .set_tags(["Frood"]).set_target_priorities(["HIGH"]).set_threat_ids(["B0RG"]).set_types(["WATCHLIST"]) \
        .set_workflows(["OPEN"]).set_watchlist_ids(["100"]).set_watchlist_names(["Gandalf"]).sort_by("name", "DESC")
    a = query.one()
    assert _was_called
    assert a.id == "S0L0"
    assert a.org_key == "Z100"
    assert a.threat_id == "B0RG"
    assert a.workflow_.state == "OPEN"


def test_query_watchlistalert_facets(monkeypatch):
    _was_called = False

    def _run_facet_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/watchlist/_facet"
        assert body == {"query": "Blort", "criteria": {"workflow": ["OPEN"]},
                        "terms": {"rows": 0, "fields": ["REPUTATION", "STATUS"]}}
        _was_called = True
        return StubResponse({"results": [{"field": {},
                                          "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                                         {"field": {},
                                          "values": [{"id": "status", "name": "statusX", "total": 9}]}]})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_facet_query)
    query = api.select(WatchlistAlert).where("Blort").set_workflows(["OPEN"])
    f = query.facets(["REPUTATION", "STATUS"])
    assert _was_called
    assert f == [{"field": {}, "values": [{"id": "reputation", "name": "reputationX", "total": 4}]},
                 {"field": {}, "values": [{"id": "status", "name": "statusX", "total": 9}]}]


def test_query_watchlistalert_invalid_criteria_values():
    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    with pytest.raises(ApiError):
        api.select(WatchlistAlert).set_watchlist_ids([888])
    with pytest.raises(ApiError):
        api.select(WatchlistAlert).set_watchlist_names([69])


def test_alerts_bulk_dismiss(monkeypatch):
    _was_called = False

    def _do_dismiss(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/workflow/_criteria"
        assert body == {"query": "Blort", "state": "DISMISSED", "remediation_state": "Fixed", "comment": "Yessir",
                        "criteria": {"device_name": ["HAL9000"]}}
        _was_called = True
        return StubResponse({"request_id": "497ABX"})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_do_dismiss)
    q = api.select(BaseAlert).where("Blort").set_device_names(["HAL9000"])
    reqid = q.dismiss("Fixed", "Yessir")
    assert _was_called
    assert reqid == "497ABX"


def test_alerts_bulk_undismiss(monkeypatch):
    _was_called = False

    def _do_update(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/workflow/_criteria"
        assert body == {"query": "Blort", "state": "OPEN", "remediation_state": "Fixed", "comment": "NoSir",
                        "criteria": {"device_name": ["HAL9000"]}}
        _was_called = True
        return StubResponse({"request_id": "497ABX"})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_do_update)
    q = api.select(BaseAlert).where("Blort").set_device_names(["HAL9000"])
    reqid = q.update("Fixed", "NoSir")
    assert _was_called
    assert reqid == "497ABX"


def test_alerts_bulk_dismiss_watchlist(monkeypatch):
    _was_called = False

    def _do_dismiss(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/watchlist/workflow/_criteria"
        assert body == {"query": "Blort", "state": "DISMISSED", "remediation_state": "Fixed", "comment": "Yessir",
                        "criteria": {"device_name": ["HAL9000"]}}
        _was_called = True
        return StubResponse({"request_id": "497ABX"})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_do_dismiss)
    q = api.select(WatchlistAlert).where("Blort").set_device_names(["HAL9000"])
    reqid = q.dismiss("Fixed", "Yessir")
    assert _was_called
    assert reqid == "497ABX"


def test_alerts_bulk_dismiss_cbanalytics(monkeypatch):
    _was_called = False

    def _do_dismiss(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/cbanalytics/workflow/_criteria"
        assert body == {"query": "Blort", "state": "DISMISSED", "remediation_state": "Fixed", "comment": "Yessir",
                        "criteria": {"device_name": ["HAL9000"]}}
        _was_called = True
        return StubResponse({"request_id": "497ABX"})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_do_dismiss)
    q = api.select(CBAnalyticsAlert).where("Blort").set_device_names(["HAL9000"])
    reqid = q.dismiss("Fixed", "Yessir")
    assert _was_called
    assert reqid == "497ABX"


def test_alerts_bulk_dismiss_vmware(monkeypatch):
    _was_called = False

    def _do_dismiss(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/alerts/vmware/workflow/_criteria"
        assert body == {"query": "Blort", "state": "DISMISSED", "remediation_state": "Fixed", "comment": "Yessir",
                        "criteria": {"device_name": ["HAL9000"]}}
        _was_called = True
        return StubResponse({"request_id": "497ABX"})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_do_dismiss)
    q = api.select(VMwareAlert).where("Blort").set_device_names(["HAL9000"])
    reqid = q.dismiss("Fixed", "Yessir")
    assert _was_called
    assert reqid == "497ABX"


def test_alerts_bulk_dismiss_threat(monkeypatch):
    _was_called = False

    def _do_dismiss(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/threat/workflow/_criteria"
        assert body == {"threat_id": ["B0RG", "F3R3NG1"], "state": "DISMISSED", "remediation_state": "Fixed",
                        "comment": "Yessir"}
        _was_called = True
        return StubResponse({"request_id": "497ABX"})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_do_dismiss)
    reqid = api.bulk_threat_dismiss(["B0RG", "F3R3NG1"], "Fixed", "Yessir")
    assert _was_called
    assert reqid == "497ABX"


def test_alerts_bulk_undismiss_threat(monkeypatch):
    _was_called = False

    def _do_update(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/threat/workflow/_criteria"
        assert body == {"threat_id": ["B0RG", "F3R3NG1"], "state": "OPEN", "remediation_state": "Fixed",
                        "comment": "NoSir"}
        _was_called = True
        return StubResponse({"request_id": "497ABX"})

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_do_update)
    reqid = api.bulk_threat_update(["B0RG", "F3R3NG1"], "Fixed", "NoSir")
    assert _was_called
    assert reqid == "497ABX"


def test_load_workflow(monkeypatch):
    _was_called = False

    def _get_workflow(url, parms=None, default=None):
        nonlocal _was_called
        assert url == "/appservices/v6/orgs/Z100/workflow/status/497ABX"
        _was_called = True
        return {"errors": [], "failed_ids": [], "id": "497ABX", "num_hits": 0, "num_success": 0, "status": "QUEUED",
                "workflow": {"state": "DISMISSED", "remediation": "Fixed", "comment": "Yessir",
                             "changed_by": "Robocop", "last_update_time": "2019-10-31T16:03:13.951Z"}}

    api = CbPSCBaseAPI(url="https://example.com", token="ABCD/1234",
                       org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_workflow)
    workflow = api.select(WorkflowStatus, "497ABX")
    assert _was_called
    assert workflow.id_ == "497ABX"
