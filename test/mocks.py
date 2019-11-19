import pytest


class MockResponse(object):
    def __init__(self, contents, scode=200):
        self._contents = contents
        self.status_code = scode

    def json(self):
        return self._contents


def failing_mock_get_object(url, parms=None, default=None):
    pytest.fail("GET called for %s when it shouldn't be" % url)


def failing_mock_post_object(url, body, **kwargs):
    pytest.fail("POST called for %s when it shouldn't be" % url)


def failing_mock_put_object(url, body, **kwargs):
    pytest.fail("PUT called for %s when it shouldn't be" % url)


def failing_mock_delete_object(url):
    pytest.fail("DELETE called for %s when it shouldn't be" % url)


_methods = {"GET": failing_mock_get_object, "POST": failing_mock_post_object,
            "PUT": failing_mock_put_object, "DELETE": failing_mock_delete_object}


class ConnectionMocks:
    @classmethod
    def get(cls, name):
        return _methods[name]
