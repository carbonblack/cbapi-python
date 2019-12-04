import pytest


class StubResponse(object):
    def __init__(self, contents, scode=200):
        self._contents = contents
        self.status_code = scode

    def json(self):
        return self._contents


def _failing_get_object(url, parms=None, default=None):
    pytest.fail("GET called for %s when it shouldn't be" % url)


def _failing_get_raw_data(url, query_params, **kwargs):
    pytest.fail("Raw GET called for %s when it shouldn't be" % url)


def _failing_post_object(url, body, **kwargs):
    pytest.fail("POST called for %s when it shouldn't be" % url)


def _failing_put_object(url, body, **kwargs):
    pytest.fail("PUT called for %s when it shouldn't be" % url)


def _failing_delete_object(url):
    pytest.fail("DELETE called for %s when it shouldn't be" % url)


def patch_cbapi(monkeypatch, api, **kwargs):
    monkeypatch.setattr(api, "get_object", kwargs.get('GET', _failing_get_object))
    monkeypatch.setattr(api, "get_raw_data", kwargs.get('RAW_GET', _failing_get_raw_data))
    monkeypatch.setattr(api, "post_object", kwargs.get('POST', _failing_post_object))
    monkeypatch.setattr(api, "put_object", kwargs.get('PUT', _failing_put_object))
    monkeypatch.setattr(api, "delete_object", kwargs.get('DELETE', _failing_delete_object))
