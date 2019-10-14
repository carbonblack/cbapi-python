from cbapi.six.moves.configparser import RawConfigParser
import os
import attrdict
import logging
import cbapi.six as six

from .errors import CredentialError

log = logging.getLogger(__name__)


default_profile = {
    "url": None,
    "token": None,
    "org_key": None,

    "ssl_verify": "True",
    "ssl_verify_hostname": "True",
    "ssl_cert_file": None,
    "ssl_force_tls_1_2": "False",

    "proxy": None,
    "ignore_system_proxy": "False",

    "rabbitmq_user": "cb",
    "rabbitmq_pass": None,
    "rabbitmq_host": "localhost",
    "rabbitmq_port": 5004
}

_boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                   '0': False, 'no': False, 'false': False, 'off': False}


class Credentials(attrdict.AttrDict):
    def __init__(self, *args, **kwargs):
        super(Credentials, self).__init__(default_profile)
        super(Credentials, self).__init__(*args, **kwargs)

        if not self.get("url", None):
            raise CredentialError("No URL specified")
        if not self.get("token", None):
            raise CredentialError("No API token specified")

        for k in ["ssl_verify", "ssl_verify_hostname", "ignore_system_proxy", "ssl_force_tls_1_2"]:
            x = self.get(k, default_profile.get(k, "True"))
            if isinstance(x, six.string_types) and x.lower() in _boolean_states:
                self[k] = _boolean_states[x.lower()]


class CredentialStoreFactory(object):

    # CredentialStore(product_name, credential_file=credential_file)
    @staticmethod
    def getCredentialStore(product_name, credential_file):
        if credential_file is None and os.environ.get('CBAPI_TOKEN', False) and os.environ.get('CBAPI_URL', False):
            log.debug("Using Envar credential store")
            return EnvarCredentialStore()
        else:
            log.debug("Using file credential store")
            return FileCredentialStore(**{"product_name": product_name, "credential_file": credential_file})


# A CredentialStore backed by os.environ rather than by a file on disk
class EnvarCredentialStore(object):
    def __init__(self):
        # `CBAPI_URL`, `CBAPI_TOKEN`, `CBAPI_SSL_VERIFY`
        environ = os.environ
        self.cbapi_url = environ.get('CBAPI_URL', None)
        self.cbapi_token = environ.get('CBAPI_TOKEN', None)
        self.cbapi_ssl_verify = environ.get('CBAPI_SSL_VERIFY', True)
        self.org_key = environ.get('CBAPI_ORG_KEY', None)
        self.credentials = Credentials(url=self.cbapi_url, token=self.cbapi_token, ssl_verify=self.cbapi_ssl_verify)

    def get_credentials(self, profile=None):
        return self.credentials


class FileCredentialStore(object):
    def __init__(self, product_name, **kwargs):
        if product_name not in ("response", "protection", "psc"):
            raise CredentialError("Product name {0:s} not valid".format(product_name))

        self.credential_search_path = [
            os.path.join(os.path.sep, "etc", "carbonblack", "credentials.%s" % product_name),
            os.path.join(os.path.expanduser("~"), ".carbonblack", "credentials.%s" % product_name),
            os.path.join(".", ".carbonblack", "credentials.%s" % product_name),
        ]

        if "credential_file" in kwargs:
            if isinstance(kwargs["credential_file"], six.string_types):
                self.credential_search_path = [kwargs["credential_file"]]
            elif type(kwargs["credential_file"]) is list:
                self.credential_search_path = kwargs["credential_file"]

        self.credentials = RawConfigParser(defaults=default_profile)
        self.credential_files = self.credentials.read(self.credential_search_path)

    def get_credentials(self, profile=None):
        credential_profile = profile or "default"
        if credential_profile not in self.get_profiles():
            raise CredentialError("Cannot find credential profile '%s' after searching in these files: %s." %
                                  (credential_profile, ", ".join(self.credential_search_path)))

        retval = {}
        for k, v in six.iteritems(default_profile):
            retval[k] = self.credentials.get(credential_profile, k)

        if not retval["url"] or not retval["token"]:
            raise CredentialError("Token and/or URL not available for profile %s" % credential_profile)

        return Credentials(retval)

    def get_profiles(self):
        return self.credentials.sections()
