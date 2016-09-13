import unittest

from nose.tools import assert_raises

from cbapi import CbEnterpriseProtectionAPI, CbEnterpriseResponseAPI
from cbapi.errors import CredentialError


class TestBasicImport(unittest.TestCase):
    def setUp(self):
        pass

    def test_import(self):
        pass

    def test_cbep_credential_error(self):
        assert_raises(CredentialError, CbEnterpriseProtectionAPI)

    def test_cber_credential_error(self):
        assert_raises(CredentialError, CbEnterpriseProtectionAPI)
