import pytest
from cbapi.psc.livequery.rest_api import CbLiveQueryAPI
from cbapi.psc.livequery.models import Run, Result
from cbapi.psc.livequery.query import ResultQuery, FacetQuery
from cbapi.errors import ApiError
from test.cbtest import StubResponse, patch_cbapi


def test_run_refresh(monkeypatch):
    _was_called = False

    def _get_run(url, parms=None, default=None):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        _was_called = True
        return {"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg", "status": "COMPLETE"}

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_run)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg", "status": "ACTIVE"})
    rc = run.refresh()
    assert _was_called
    assert rc
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"
    assert run.status == "COMPLETE"


def test_run_stop(monkeypatch):
    _was_called = False

    def _execute_stop(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/status"
        assert body == {"status": "CANCELLED"}
        _was_called = True
        return StubResponse({"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg", "status": "CANCELLED"})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, PUT=_execute_stop)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg", "status": "ACTIVE"})
    rc = run.stop()
    assert _was_called
    assert rc
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"
    assert run.status == "CANCELLED"


def test_run_stop_failed(monkeypatch):
    _was_called = False

    def _execute_stop(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/status"
        assert body == {"status": "CANCELLED"}
        _was_called = True
        return StubResponse({"error_message": "The query is not presently running."}, 409)

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, PUT=_execute_stop)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg", "status": "CANCELLED"})
    rc = run.stop()
    assert _was_called
    assert not rc


def test_run_delete(monkeypatch):
    _was_called = False

    def _execute_delete(url):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        if _was_called:
            pytest.fail("_execute_delete should not be called twice!")
        _was_called = True
        return StubResponse(None)

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, DELETE=_execute_delete)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg", "status": "ACTIVE"})
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

    def _execute_delete(url):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        _was_called = True
        return StubResponse(None, 403)

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, DELETE=_execute_delete)
    run = Run(api, "abcdefg", {"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg", "status": "ACTIVE"})
    rc = run.delete()
    assert _was_called
    assert not rc
    assert not run._is_deleted


def test_result_device_summaries(monkeypatch):
    _was_called = False

    def _run_summaries(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/results/device_summaries/_search"
        assert body == {"query": "foo", "criteria": {"device_name": ["AxCx", "A7X"]},
                        "sort": [{"field": "device_name", "order": "ASC"}], "start": 0}
        _was_called = True
        return StubResponse({"org_key": "Z100", "num_found": 2,
                             "results": [{"id": "ghijklm", "total_results": 2, "device_id": 314159,
                                          "metrics": [{"key": "aaa", "value": 0.0}, {"key": "bbb", "value": 0.0}]},
                                         {"id": "mnopqrs", "total_results": 3, "device_id": 271828,
                                          "metrics": [{"key": "aaa", "value": 0.0}, {"key": "bbb", "value": 0.0}]}]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_summaries)
    result = Result(api, {"id": "abcdefg", "device": {"id": "abcdefg"}, "fields": {}, "metrics": {}})
    query = result.query_device_summaries().where("foo").criteria(device_name=["AxCx", "A7X"]).sort_by("device_name")
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

    def _run_facets(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/results/_facet"
        assert body == {"query": "xyzzy", "criteria": {"device_name": ["AxCx", "A7X"]},
                        "terms": {"fields": ["alpha", "bravo", "charlie"]}}
        _was_called = True
        return StubResponse({"terms": [{"field": "alpha", "values": [{"total": 1, "id": "alpha1", "name": "alpha1"},
                                                                     {"total": 2, "id": "alpha2", "name": "alpha2"}]},
                                       {"field": "bravo", "values": [{"total": 1, "id": "bravo1", "name": "bravo1"},
                                                                     {"total": 2, "id": "bravo2", "name": "bravo2"}]},
                                       {"field": "charlie", "values": [{"total": 1, "id": "charlie1",
                                                                        "name": "charlie1"},
                                                                       {"total": 2, "id": "charlie2",
                                                                        "name": "charlie2"}]}]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_facets)
    result = Result(api, {"id": "abcdefg", "device": {"id": "abcdefg"}, "fields": {}, "metrics": {}})
    query = result.query_result_facets().where("xyzzy").facet_field("alpha").facet_field(["bravo", "charlie"]) \
        .criteria(device_name=["AxCx", "A7X"])
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

    def _run_facets(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg/results/device_summaries/_facet"
        assert body == {"query": "xyzzy", "criteria": {"device_name": ["AxCx", "A7X"]},
                        "terms": {"fields": ["alpha", "bravo", "charlie"]}}
        _was_called = True
        return StubResponse({"terms": [{"field": "alpha", "values": [{"total": 1, "id": "alpha1", "name": "alpha1"},
                                                                     {"total": 2, "id": "alpha2", "name": "alpha2"}]},
                                       {"field": "bravo", "values": [{"total": 1, "id": "bravo1", "name": "bravo1"},
                                                                     {"total": 2, "id": "bravo2", "name": "bravo2"}]},
                                       {"field": "charlie", "values": [{"total": 1, "id": "charlie1",
                                                                        "name": "charlie1"},
                                                                       {"total": 2, "id": "charlie2",
                                                                        "name": "charlie2"}]}]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_facets)
    result = Result(api, {"id": "abcdefg", "device": {"id": "abcdefg"}, "fields": {}, "metrics": {}})
    query = result.query_device_summary_facets().where("xyzzy").facet_field("alpha") \
        .facet_field(["bravo", "charlie"]).criteria(device_name=["AxCx", "A7X"])
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
