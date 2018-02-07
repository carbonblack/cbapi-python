from cbapi.connection import CbAPISessionAdapter, check_python_tls_compatibility
from nose.tools import assert_equal, assert_raises
import unittest
import requests
import sys
import os

sys.path.append(os.path.dirname(__file__))
import requests_cache


class TestTLS(unittest.TestCase):
    def setUp(self):
        requests_cache.uninstall_cache()
        self.tls_adapter = CbAPISessionAdapter(force_tls_1_2=True)
        self.session = requests.Session()
        self.session.mount("https://", self.tls_adapter)

    def test_tls_v1_2(self):
        rating = self.session.get("https://www.howsmyssl.com/a/check").json()["rating"]
        assert_equal(rating, "Probably Okay")

    def test_tls_v1_0(self):
        assert_raises(Exception, self.session.get, "https://tls-v1-0.badssl.com:1010/")

    def test_tls_v1_1(self):
        assert_raises(Exception, self.session.get, "https://tls-v1-0.badssl.com:1011/")

    def test_tls_version_checker(self):
        assert_equal(check_python_tls_compatibility(), "TLSv1.2")
