import pytest
from cbapi.psc.livequery.rest_api import CbLiveQueryAPI
from cbapi.psc.livequery.models import Run
from cbapi.psc.livequery.query import RunQuery, RunHistoryQuery
from cbapi.errors import ApiError, CredentialError
from test.mocks import MockResponse, ConnectionMocks

def test_no_org_key():
    with pytest.raises(CredentialError):
        api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                             ssl_verify=True) # note: no org_key
    
        
def test_simple_get(monkeypatch):
    _was_called = False
    
    def mock_get_object(url, parms=None, default=None):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/abcdefg"
        assert parms is None
        assert default is None
        _was_called = True
        return {"org_key":"Z100", "name":"FoobieBletch", "id":"abcdefg"}
    
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", mock_get_object)
    monkeypatch.setattr(api, "post_object", ConnectionMocks.get("POST"))
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    run = api.select(Run, "abcdefg")
    assert _was_called
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"
    
    
def test_query(monkeypatch):
    _was_called = False
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs"
        assert body["sql"] == "select * from whatever;"
        _was_called = True
        return MockResponse({"org_key":"Z100", "name":"FoobieBletch", "id":"abcdefg"})
    
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.query("select * from whatever;");
    assert isinstance(query, RunQuery)
    run = query.submit()
    assert _was_called
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"
    
    
def test_query_with_everything(monkeypatch):
    _was_called = False

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs"
        assert body["sql"] == "select * from whatever;"
        assert body["name"] == "AmyWasHere"
        assert body["notify_on_finish"] == True
        df = body["device_filter"]
        assert df["device_ids"] == [1, 2, 3]
        assert df["device_types"] == ["Alpha", "Bravo", "Charlie"]
        assert df["policy_ids"] == [16, 27, 38]
        _was_called = True
        return MockResponse({"org_key":"Z100", "name":"FoobieBletch", "id":"abcdefg"})
    
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
    query = api.query("select * from whatever;").device_ids([1, 2, 3])
    query = query.device_types(["Alpha", "Bravo", "Charlie"]);
    query = query.policy_ids([16, 27, 38])
    query = query.name("AmyWasHere").notify_on_finish()
    assert isinstance(query, RunQuery)
    run = query.submit()
    assert _was_called
    assert run.org_key == "Z100"
    assert run.name == "FoobieBletch"
    assert run.id == "abcdefg"
    
    
def test_query_device_ids_broken():
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    query = api.query("select * from whatever;");
    with pytest.raises(ApiError):
        query = query.device_ids(["Bogus"])
    
    
def test_query_device_types_broken():
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    query = api.query("select * from whatever;");
    with pytest.raises(ApiError):
        query = query.device_types([420]);
    
    
def test_query_policy_ids_broken():
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    query = api.query("select * from whatever;");
    with pytest.raises(ApiError):
        query = query.policy_ids(["Bogus"])
    
    
def test_query_history(monkeypatch):
    _was_called = False 
    
    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/_search"
        assert body["query"] == "xyzzy"
        _was_called = True 
        run1 = {"org_key":"Z100", "name":"FoobieBletch", "id":"abcdefg"}
        run2 = {"org_key":"Z100", "name":"Aoxomoxoa", "id":"cdefghi"}
        run3 = {"org_key":"Z100", "name":"Read_Me", "id":"efghijk"}
        return MockResponse({"org_key":"Z100", "num_found":3, "results":[run1, run2, run3]})      
    
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
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

    def mock_post_object(url, body, **kwargs):
        nonlocal _was_called
        assert url == "/livequery/v1/orgs/Z100/runs/_search"
        assert body["query"] == "xyzzy"
        t = body["sort"][0]
        assert t["field"] == "id"
        assert t["order"] == "ASC"
        _was_called = True 
        run1 = {"org_key":"Z100", "name":"FoobieBletch", "id":"abcdefg"}
        run2 = {"org_key":"Z100", "name":"Aoxomoxoa", "id":"cdefghi"}
        run3 = {"org_key":"Z100", "name":"Read_Me", "id":"efghijk"}
        return MockResponse({"org_key":"Z100", "num_found":3, "results":[run1, run2, run3]})      
        
    api = CbLiveQueryAPI(url="https://example.com", token="ABCD/1234",
                         org_key="Z100", ssl_verify=True)
    monkeypatch.setattr(api, "get_object", ConnectionMocks.get("GET"))
    monkeypatch.setattr(api, "post_object", mock_post_object)
    monkeypatch.setattr(api, "put_object", ConnectionMocks.get("PUT"))
    monkeypatch.setattr(api, "delete_object", ConnectionMocks.get("DELETE"))
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
    