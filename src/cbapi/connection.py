#!/usr/bin/env python

from __future__ import absolute_import

import requests
import sys
from requests.adapters import HTTPAdapter, DEFAULT_POOLBLOCK, DEFAULT_RETRIES, DEFAULT_POOLSIZE

try:
    from requests.packages.urllib3.util.ssl_ import create_urllib3_context
    REQUESTS_HAS_URLLIB_SSL_CONTEXT = True
except ImportError:
    REQUESTS_HAS_URLLIB_SSL_CONTEXT = False

import ssl


# Older versions of requests (such as the one packaged with Splunk) do not have a Retry object
# in the packaged version of urllib3. Fall back gracefully.
try:
    from requests.packages.urllib3 import Retry
    MAX_RETRIES = Retry(total=5, status_forcelist=[502, 504], backoff_factor=0.5)
except ImportError:
    MAX_RETRIES = 5

from requests.packages.urllib3.poolmanager import PoolManager

import logging
import json

from cbapi.six import iteritems
from cbapi.six.moves import urllib

from .auth import CredentialStoreFactory, Credentials
from .errors import ServerError, TimeoutError, ApiError, ObjectNotFoundError, UnauthorizedError, CredentialError, \
    ConnectionError
from . import __version__

from .cache.lru import lru_cache_function
from .models import CreatableModelMixin
from .utils import calculate_elapsed_time, convert_query_params

log = logging.getLogger(__name__)


def check_python_tls_compatibility():
    try:
        tls_adapter = CbAPISessionAdapter(force_tls_1_2=True)
    except Exception as e:
        ret = "TLSv1.1"

        if "OP_NO_TLSv1_1" not in ssl.__dict__:
            ret = "TLSv1.0"
        elif "OP_NO_TLSv1" not in ssl.__dict__:
            ret = "SSLv3"
        elif "OP_NO_SSLv3" not in ssl.__dict__:
            ret = "SSLv2"
        else:
            ret = "Unknown"
    else:
        ret = "TLSv1.2"

    return ret


class CbAPISessionAdapter(HTTPAdapter):
    def __init__(self, verify_hostname=True, force_tls_1_2=False, max_retries=DEFAULT_RETRIES, **pool_kwargs):
        self._cbapi_verify_hostname = verify_hostname
        self._cbapi_force_tls_1_2 = force_tls_1_2

        if force_tls_1_2 and not REQUESTS_HAS_URLLIB_SSL_CONTEXT:
            raise ApiError("Cannot force the use of TLS1.2: Python, urllib3, and requests versions are too old.")

        super(CbAPISessionAdapter, self).__init__(max_retries=max_retries, **pool_kwargs)

    def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs):
        if self._cbapi_force_tls_1_2 and REQUESTS_HAS_URLLIB_SSL_CONTEXT:
            # Force the use of TLS v1.2 when talking to this Cb Response server.
            context = create_urllib3_context(ciphers=('TLSv1.2:!aNULL:!eNULL:!MD5'))
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            pool_kwargs['ssl_context'] = context

        if not self._cbapi_verify_hostname:
            # Provide the ability to validate a Carbon Black server's SSL certificate without validating the hostname
            # (by default Carbon Black certificates are "issued" as CN=Self-signed Carbon Black Enterprise Server
            # HTTPS Certificate)
            pool_kwargs["assert_hostname"] = False

        return super(CbAPISessionAdapter, self).init_poolmanager(connections, maxsize, block, **pool_kwargs)


class Connection(object):
    def __init__(self, credentials, integration_name=None, timeout=None, max_retries=None, **pool_kwargs):
        if not credentials.url or not credentials.url.startswith("https://"):
            raise ConnectionError("Server URL must be a URL: eg. https://localhost")

        if not credentials.token:
            raise ConnectionError("No API token provided")

        self.server = credentials.url.rstrip("/")
        self.ssl_verify = credentials.ssl_verify

        if not self.ssl_verify:
            try:
                from requests.packages.urllib3.exceptions import InsecureRequestWarning
                requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            except Exception:
                pass
        else:
            if credentials.ssl_cert_file:
                self.ssl_verify = credentials.ssl_cert_file

        user_agent = "cbapi/{0:s} Python/{1:d}.{2:d}.{3:d}".format(__version__,
                             sys.version_info[0], sys.version_info[1], sys.version_info[2])
        if integration_name:
            user_agent += " {}".format(integration_name)

        self.token = credentials.token
        self.token_header = {'X-Auth-Token': self.token, 'User-Agent': user_agent}
        self.session = requests.Session()

        self._timeout = timeout

        if max_retries is None:
            max_retries = MAX_RETRIES

        try:
            tls_adapter = CbAPISessionAdapter(max_retries=max_retries, force_tls_1_2=credentials.ssl_force_tls_1_2,
                                              verify_hostname=credentials.ssl_verify_hostname, **pool_kwargs)
        except ssl.SSLError as e:
            raise ApiError("This version of Python and OpenSSL do not support TLSv1.2: {}".format(e),
                           original_exception=e)
        except Exception as e:
            raise ApiError("Unknown error establishing cbapi session: {0}: {1}".format(e.__class__.__name__, e),
                           original_exception=e)

        self.session.mount(self.server, tls_adapter)

        self.proxies = {}
        if credentials.ignore_system_proxy:         # see https://github.com/kennethreitz/requests/issues/879
            # Unfortunately, requests will look for any proxy-related environment variables and use those anyway. The
            # only way to solve this without side effects, is passing in empty strings for 'http' and 'https':
            self.proxies = {
                'http': '',
                'https': '',
                'no': 'pass'
            }
        else:
            if credentials.proxy:
                self.proxies['http'] = credentials.proxy
                self.proxies['https'] = credentials.proxy

    def http_request(self, method, url, **kwargs):
        method = method.upper()

        verify_ssl = kwargs.pop('verify', None) or self.ssl_verify
        proxies = kwargs.pop('proxies', None) or self.proxies

        new_headers = kwargs.pop('headers', None)
        if new_headers:
            headers = self.token_header.copy()
            headers.update(new_headers)
        else:
            headers = self.token_header

        uri = self.server + url

        try:
            raw_data = kwargs.get("data", None)
            if raw_data:
                log.debug("Sending HTTP {0} {1} with {2}".format(method, url, raw_data))
            r = self.session.request(method, uri, headers=headers, verify=verify_ssl, proxies=proxies,
                                     timeout=self._timeout, **kwargs)
            log.debug('HTTP {0:s} {1:s} took {2:.3f}s (response {3:d})'.format(method, url,
                                                                               calculate_elapsed_time(r.elapsed),
                                                                               r.status_code))
        except requests.Timeout as timeout_error:
            raise TimeoutError(uri=uri, original_exception=timeout_error)
        except requests.ConnectionError as connection_error:
            raise ApiError("Received a network connection error from {0:s}: {1:s}".format(self.server,
                                                                                          str(connection_error)),
                           original_exception=connection_error)
        except Exception as e:
            raise ApiError("Unknown exception when connecting to server: {0:s}".format(str(e)),
                           original_exception=e)
        else:
            if r.status_code == 404:
                raise ObjectNotFoundError(uri=uri, message=r.text)
            elif r.status_code == 401:
                raise UnauthorizedError(uri=uri, action=method, message=r.text)
            elif r.status_code >= 400:
                raise ServerError(error_code=r.status_code, message=r.text)
            return r

    def get(self, url, **kwargs):
        return self.http_request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.http_request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.http_request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.http_request("DELETE", url, **kwargs)


class BaseAPI(object):
    """baseapi"""
    def __init__(self, *args, **kwargs):
        product_name = kwargs.pop("product_name", None)
        credential_file = kwargs.pop("credential_file", None)
        integration_name = kwargs.pop("integration_name", None)
        self.credential_store = CredentialStoreFactory.getCredentialStore(product_name,credential_file)

        url, token, org_key = kwargs.pop("url", None), kwargs.pop("token", None), kwargs.pop("org_key", None)
        if url and token:
            if org_key:
                credentials = {"url": url, "token": token, "org_key": org_key}
            else:
                credentials = {"url": url, "token": token}

            for k in ("ssl_verify",):
                if k in kwargs:
                    credentials[k] = kwargs.pop(k)
            self.credentials = Credentials(credentials)
            self.credential_profile_name = None
        else:
            self.credential_profile_name = kwargs.pop("profile", None)
            self.credentials = self.credential_store.get_credentials(self.credential_profile_name)

        timeout = kwargs.pop("timeout", None)
        max_retries = kwargs.pop("max_retries", None)
        pool_connections = kwargs.pop("pool_connections", DEFAULT_POOLSIZE)
        pool_maxsize = kwargs.pop("pool_maxsize", DEFAULT_POOLSIZE)
        pool_block = kwargs.pop("pool_block", DEFAULT_POOLBLOCK)

        self.session = Connection(self.credentials, integration_name=integration_name, timeout=timeout,
                                  max_retries=max_retries, pool_connections=pool_connections,
                                  pool_maxsize=pool_maxsize, pool_block=pool_block)

    def raise_unless_json(self, ret, expected):
        if ret.status_code == 200:
            message = ret.json()
            for k, v in iteritems(expected):
                if k not in message or message[k] != v:
                    raise ServerError(ret.status_code, message)
        else:
            raise ServerError(ret.status_code, "".format(ret.content), )

    def get_object(self, uri, query_parameters=None, default=None):
        if query_parameters:
            if isinstance(query_parameters, dict):
                query_parameters = convert_query_params(query_parameters)
            uri += '?%s' % (urllib.parse.urlencode(sorted(query_parameters)))

        result = self.api_json_request("GET", uri)
        if result.status_code == 200:
            try:
                return result.json()
            except:
                raise ServerError(result.status_code, "Cannot parse response as JSON: {0:s}".format(result.content))
        elif result.status_code == 204:
            # empty response
            return default
        else:
            raise ServerError(error_code=result.status_code, message="Unknown error: {0}".format(result.content))

    def api_json_request(self, method, uri, **kwargs):
        headers = kwargs.pop("headers", {})
        raw_data = None

        if method in ("POST", "PUT", "PATCH"):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
                raw_data = kwargs.pop("data", {})
                raw_data = json.dumps(raw_data, sort_keys=True)

        result = self.session.http_request(method, uri, headers=headers, data=raw_data, **kwargs)

        try:
            resp = result.json()
        except:
            return result

        if "errorMessage" in resp:
            raise ServerError(error_code=result.status_code, message=resp["errorMessage"])

        return result

    def post_object(self, uri, body, **kwargs):
        return self.api_json_request("POST", uri, data=body, **kwargs)

    def put_object(self, uri, body, **kwargs):
        return self.api_json_request("PUT", uri, data=body, **kwargs)

    def delete_object(self, uri):
        return self.api_json_request("DELETE", uri)

    def select(self, cls, unique_id=None, *args, **kwargs):
        """Prepares a query against the Carbon Black data store.

        :param class cls: The Model class (for example, Computer, Process, Binary, FileInstance) to query
        :param unique_id: (optional) The unique id of the object to retrieve, to retrieve a single object by ID

        :returns: An instance of the Model class if a unique_id is provided, otherwise a Query object
        """
        if unique_id is not None:
            return select_instance(self, cls, unique_id, *args, **kwargs)
        else:
            return self._perform_query(cls, **kwargs)

    def create(self, cls, data=None):
        """Creates a new object.

        :param class cls: The Model class (only some models can be created, for example, Feed, Notification, ...)

        :returns: An empty instance of the Model class
        :raises ApiError: if the Model cannot be created
        """
        if issubclass(cls, CreatableModelMixin):
            n = cls(self)
            if type(data) is dict:
                for k, v in iteritems(data):
                    setattr(n, k, v)
            return n
        else:
            raise ApiError("Cannot create object of type {0:s}".format(cls.__name__))

    def _perform_query(self, cls, **kwargs):
        pass

    @property
    def url(self):
        return self.session.server


# by default, set expiration to 1 minute and max_size to 1k elements
# TODO: how does this interfere with mutable objects?
@lru_cache_function(max_size=1024, expiration=1*60)
def select_instance(api, cls, unique_id, *args, **kwargs):
    return cls(api, unique_id, *args, **kwargs)
