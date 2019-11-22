import pytest
from cbapi.psc.livequery.rest_api import CbLiveQueryAPI
from cbapi.psc.livequery.models import Run
from cbapi.psc.livequery.query import RunQuery, RunHistoryQuery
from cbapi.errors import ApiError, CredentialError
from test.cbtest import StubResponse, patch_cbapi


def test_no_org_key():
    with pytest.raises(CredentialError):
        CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", ssl_verify=True)  # note: no org_key


def test_simple_get(monkeypatch):
    _was_called = False

    def _get_run(url, parms=None, default=None):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        _was_called = True
        return {"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg"}

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, GET=_get_run)
    run = api.select(Run, "abcdefg")
    assert _was_called
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"


def test_query(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs"
        assert body == {"sql": "select * from whatever;", "device_filter": {}}
        _was_called = True
        return StubResponse({"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg"})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.query("select * from whatever;")
    assert isinstance(query, RunQuery)
    run = query.submit()
    assert _was_called
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"


def test_query_with_everything(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs"
        assert body == {"sql": "select * from whatever;", "name": "AmyWasHere", "notify_on_finish": True,
                        "device_filter": {"device_ids": [1, 2, 3], "device_types": ["Alpha", "Bravo", "Charlie"],
                                          "policy_ids": [16, 27, 38]}}
        _was_called = True
        return StubResponse({"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg"})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.query("select * from whatever;").device_ids([1, 2, 3]).device_types(["Alpha", "Bravo", "Charlie"]) \
        .policy_ids([16, 27, 38]).name("AmyWasHere").notify_on_finish()
    assert isinstance(query, RunQuery)
    run = query.submit()
    assert _was_called
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"


def test_query_device_ids_broken():
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    query = api.query("select * from whatever;")
    with pytest.raises(ApiError):
        query = query.device_ids(["Bogus"])


def test_query_device_types_broken():
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    query = api.query("select * from whatever;")
    with pytest.raises(ApiError):
        query = query.device_types([420])


def test_query_policy_ids_broken():
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    query = api.query("select * from whatever;")
    with pytest.raises(ApiError):
        query = query.policy_ids(["Bogus"])


def test_query_history(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/_search"
        assert body == {"query": "xyzzy", "start": 0}
        _was_called = True
        return StubResponse({"org_key": "Z100", "num_found": 3,
                             "results": [{"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg"},
                                         {"org_key": "Z100", "name": "Aoxomoxoa", "id": "cdefghi"},
                                         {"org_key": "Z100", "name": "Read_Me", "id": "efghijk"}]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.query_history("xyzzy")
    assert isinstance(query, RunHistoryQuery)
    count = 0
    for item in query.all():
        assert item.org_key == "Z100"
        if item.id == "abcdefg":
            assert item.name == "FoobieBletch"
        elif item.id == "cdefghi":
            assert item.name == "Aoxomoxoa"
        elif item.id == "efghijk":
            assert item.name == "Read_Me"
        else:
            pytest.fail("Unknown item ID: %s" % item.id)
        count = count + 1
    assert _was_called
    assert count == 3


def test_query_history_with_everything(monkeypatch):
    _was_called = False

    def _run_query(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/_search"
        assert body == {"query": "xyzzy", "sort": [{"field": "id", "order": "ASC"}], "start": 0}
        _was_called = True
        return StubResponse({"org_key": "Z100", "num_found": 3,
                             "results": [{"org_key": "Z100", "name": "FoobieBletch", "id": "abcdefg"},
                                         {"org_key": "Z100", "name": "Aoxomoxoa", "id": "cdefghi"},
                                         {"org_key": "Z100", "name": "Read_Me", "id": "efghijk"}]})

    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234", org_key="Z100", ssl_verify=True)
    patch_cbapi(monkeypatch, api, POST=_run_query)
    query = api.query_history("xyzzy").sort_by("id")
    assert isinstance(query, RunHistoryQuery)
    count = 0
    for item in query.all():
        assert item.org_key == "Z100"
        if item.id == "abcdefg":
            assert item.name == "FoobieBletch"
        elif item.id == "cdefghi":
            assert item.name == "Aoxomoxoa"
        elif item.id == "efghijk":
            assert item.name == "Read_Me"
        else:
            pytest.fail("Unknown item ID: %s" % item.id)
        count = count + 1
    assert _was_called
    assert count == 3
