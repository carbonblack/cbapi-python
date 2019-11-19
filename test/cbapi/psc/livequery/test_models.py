import pytest
from cbapi.psc.livequery.rest_api import CbLiveQueryAPI
from cbapi.psc.livequery.models import Run, Result
from cbapi.psc.livequery.query import ResultQuery, FacetQuery
from cbapi.errors import ApiError
from test.mocks import MockResponse, ConnectionMocks


def test_run_refresh(monkeypatch):
    _was_called = False

    def mock_get_object(url, parms=None, default=None):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        assert parms is None
        assert default is None
        _was_called = True
        return {"org_key": "Z100", "name": "FoobieBletch",
                "id": "abcdefg", "status": "COMPLETE"}

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch",
                               "id": "abcdefg", "status": "ACTIVE"})
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    rc = run.refresh()
    assert _was_called
    assert rc
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"
    assert run.status == "COMPLETE"


def test_run_stop(monkeypatch):
    _was_called = False

    def mock_put_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/status"
        assert body["status"] == "CANCELLED"
        _was_called = True
        return MockResponse({"org_key": "Z100", "name": "FoobieBletch",
                             "id": "abcdefg", "status": "CANCELLED"})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch",
                               "id": "abcdefg", "status": "ACTIVE"})
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", mock_put_object)
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    rc = run.stop()
    assert _was_called
    assert rc
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"
    assert run.status == "CANCELLED"


def test_run_stop_failed(monkeypatch):
    _was_called = False

    def mock_put_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/status"
        assert body["status"] == "CANCELLED"
        _was_called = True
        return MockResponse({"error_message": "The query is not presently running."}, 409)

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch",
                               "id": "abcdefg", "status": "CANCELLED"})
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", mock_put_object)
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    rc = run.stop()
    assert _was_called
    assert not rc


def test_run_delete(monkeypatch):
    _was_called = False

    def mock_delete_object(url):
        nonlocal _was_called
        if _was_called:
            pytest.fail("delete should not be called twice!")
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        _was_called = True
        return MockResponse(None)

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch",
                               "id": "abcdefg", "status": "ACTIVE"})
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", mock_delete_object)
    rc = run.delete()
    assert _was_called
    assert rc
    assert run._is_deleted
    # Now ensure that certain operations that don't make sense on a deleted object raise ApiError
    with pytest.raises(ApiError):
        run.refresh()
    with pytest.raises(ApiError):
        run.stop()
    # And make sure that deleting a deleted object returns True immediately
    rc = run.delete()
    assert rc


def test_run_delete_failed(monkeypatch):
    _was_called = False

    def mock_delete_object(url):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        _was_called = True
        return MockResponse(None, 403)

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch",
                               "id": "abcdefg", "status": "ACTIVE"})
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", mock_delete_object)
    rc = run.delete()
    assert _was_called
    assert not rc
    assert not run._is_deleted


def test_result_device_summaries(monkeypatch):
    _was_called = False

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/results/device_summaries/_search"
        assert body["query"] == "foo"
        t = body["criteria"]
        assert t["device_name"] == ["AxCx", "A7X"]
        t = body["sort"][0]
        assert t["field"] == "device_name"
        assert t["order"] == "ASC"
        _was_called = True
        metrics = [{"key": "aaa", "value": 0.0}, {"key": "bbb", "value": 0.0}]
        res1 = {"id": "ghijklm", "total_results": 2, "device_id": 314159, "metrics": metrics}
        res2 = {"id": "mnopqrs", "total_results": 3, "device_id": 271828, "metrics": metrics}
        return MockResponse({"org_key": "Z100", "num_found": 2, "results": [res1, res2]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    tmp_id = {"id": "abcdefg"}
    result = Result(api, {"id": "abcdefg", "device": tmp_id, "fields": {}, "metrics": {}})
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = result.query_device_summaries().where("foo").criteria(device_name=["AxCx", "A7X"])
    query = query.sort_by("device_name")
    assert isinstance(query, ResultQuery)
    count = 0
    for item in query.all():
        if item.id == "ghijklm":
            assert item.total_results == 2
            assert item.device_id == 314159
        elif item.id == "mnopqrs":
            assert item.total_results == 3
            assert item.device_id == 271828
        else:
            pytest.fail("Invalid object with ID %s seen" % item.id)
        count = count + 1
    assert _was_called
    assert count == 2


def test_result_query_result_facets(monkeypatch):
    _was_called = False

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/results/_facet"
        assert body["query"] == "xyzzy"
        t = body["criteria"]
        assert t["device_name"] == ["AxCx", "A7X"]
        t = body["terms"]
        assert t["fields"] == ["alpha", "bravo", "charlie"]
        _was_called = True
        v1 = {"total": 1, "id": "alpha1", "name": "alpha1"}
        v2 = {"total": 2, "id": "alpha2", "name": "alpha2"}
        term1 = {"field": "alpha", "values": [v1, v2]}
        v1 = {"total": 1, "id": "bravo1", "name": "bravo1"}
        v2 = {"total": 2, "id": "bravo2", "name": "bravo2"}
        term2 = {"field": "bravo", "values": [v1, v2]}
        v1 = {"total": 1, "id": "charlie1", "name": "charlie1"}
        v2 = {"total": 2, "id": "charlie2", "name": "charlie2"}
        term3 = {"field": "charlie", "values": [v1, v2]}
        return MockResponse({"terms": [term1, term2, term3]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    tmp_id = {"id": "abcdefg"}
    result = Result(api, {"id": "abcdefg", "device": tmp_id, "fields": {}, "metrics": {}})
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = result.query_result_facets().where("xyzzy")
    query = query.facet_field("alpha").facet_field(["bravo", "charlie"])
    query = query.criteria(device_name=["AxCx", "A7X"])
    assert isinstance(query, FacetQuery)
    count = 0
    for item in query.all():
        vals = item.values
        if item.field == "alpha":
            assert vals[0]["id"] == "alpha1"
            assert vals[1]["id"] == "alpha2"
        elif item.field == "bravo":
            assert vals[0]["id"] == "bravo1"
            assert vals[1]["id"] == "bravo2"
        elif item.field == "charlie":
            assert vals[0]["id"] == "charlie1"
            assert vals[1]["id"] == "charlie2"
        else:
            pytest.fail("Unknown field name %s seen" % item.field)
        count = count + 1
    assert _was_called
    assert count == 3


def test_result_query_device_summary_facets(monkeypatch):
    _was_called = False

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/results/device_summaries/_facet"
        assert body["query"] == "xyzzy"
        t = body["criteria"]
        assert t["device_name"] == ["AxCx", "A7X"]
        t = body["terms"]
        assert t["fields"] == ["alpha", "bravo", "charlie"]
        _was_called = True
        v1 = {"total": 1, "id": "alpha1", "name": "alpha1"}
        v2 = {"total": 2, "id": "alpha2", "name": "alpha2"}
        term1 = {"field": "alpha", "values": [v1, v2]}
        v1 = {"total": 1, "id": "bravo1", "name": "bravo1"}
        v2 = {"total": 2, "id": "bravo2", "name": "bravo2"}
        term2 = {"field": "bravo", "values": [v1, v2]}
        v1 = {"total": 1, "id": "charlie1", "name": "charlie1"}
        v2 = {"total": 2, "id": "charlie2", "name": "charlie2"}
        term3 = {"field": "charlie", "values": [v1, v2]}
        return MockResponse({"terms": [term1, term2, term3]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    tmp_id = {"id": "abcdefg"}
    result = Result(api, {"id": "abcdefg", "device": tmp_id, "fields": {}, "metrics": {}})
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = result.query_device_summary_facets().where("xyzzy")
    query = query.facet_field("alpha").facet_field(["bravo", "charlie"])
    query = query.criteria(device_name=["AxCx", "A7X"])
    assert isinstance(query, FacetQuery)
    count = 0
    for item in query.all():
        vals = item.values
        if item.field == "alpha":
            assert vals[0]["id"] == "alpha1"
            assert vals[1]["id"] == "alpha2"
        elif item.field == "bravo":
            assert vals[0]["id"] == "bravo1"
            assert vals[1]["id"] == "bravo2"
        elif item.field == "charlie":
            assert vals[0]["id"] == "charlie1"
            assert vals[1]["id"] == "charlie2"
        else:
            pytest.fail("Unknown field name %s seen" % item.field)
        count = count + 1
    assert _was_called
    assert count == 3
