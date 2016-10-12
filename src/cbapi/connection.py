#!/usr/bin/env python

from __future__ import absolute_import

import requests
import sys
from requests.adapters import HTTPAdapter

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

from six import iteritems
from six.moves import urllib

from .auth import CredentialStore, Credentials
from .errors import ServerError, TimeoutError, ApiError, ObjectNotFoundError, UnauthorizedError, CredentialError
from . import __version__

from .cache.lru import lru_cache_function
from .models import CreatableModelMixin


log = logging.getLogger(__name__)


def calculate_elapsed_time_new(td):
    return td.total_seconds()


def calculate_elapsed_time_old(td):
    return float((td.microseconds +
                  (td.seconds + td.days * 24 * 3600) * 10**6)) / 10**6


if sys.version_info < (2, 7):
    calculate_elapsed_time = calculate_elapsed_time_old
else:
    calculate_elapsed_time = calculate_elapsed_time_new

# Provide the ability to validate a Carbon Black server's SSL certificate without validating the hostname
# (by default Carbon Black certificates are "issued" as CN=Self-signed Carbon Black Enterprise Server HTTPS Certificate)
class HostNameIgnoringAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       assert_hostname=False, **pool_kwargs)


class ConnectionError(Exception):
    pass


class Connection(object):
    def __init__(self, credentials, integration_name=None):
        if not credentials.url or not credentials.url.startswith(("https://", "http://")):
            raise ConnectionError("Server URL must be a URL: eg. https://localhost")

        if credentials.url.startswith("http://"):
            log.warning("Connecting to Cb server on unencrypted HTTP")

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

        user_agent = "cbapi/{0:s} Python/{1:d}.{2:d}.{3:d}".format(__version__,
                             sys.version_info[0], sys.version_info[1], sys.version_info[2])
        if integration_name:
            user_agent += " {}".format(integration_name)

        self.token = credentials.token
        self.token_header = {'X-Auth-Token': self.token, 'User-Agent': user_agent}
        self.session = requests.Session()

        if not credentials.ssl_verify_hostname:
            self.session.mount(self.server, HostNameIgnoringAdapter())

        # TODO: apply this to the ssl_verify_hostname case as well
        self.session.mount(self.server, HTTPAdapter(max_retries=MAX_RETRIES))

        self.proxies = {}
        if credentials.ignore_system_proxy:         # see https://github.com/kennethreitz/requests/issues/879
            self.proxies = {
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
            r = self.session.request(method, uri, headers=headers, verify=verify_ssl, proxies=proxies, **kwargs)
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
                raise ObjectNotFoundError(uri=uri, message=r.content)
            elif r.status_code == 401:
                raise UnauthorizedError(uri=uri, action=method, message=r.content)
            elif r.status_code >= 400:
                raise ServerError(error_code=r.status_code, message=r.content)
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

        self.credential_store = CredentialStore(product_name, credential_file=credential_file)

        url, token = kwargs.pop("url", None), kwargs.pop("token", None)
        if url and token:
            credentials = {"url": url, "token": token}

            for k in ("ssl_verify",):
                if k in kwargs:
                    credentials[k] = kwargs.pop(k)
            self.credentials = Credentials(credentials)
            self.credential_profile_name = None
        else:
            self.credential_profile_name = kwargs.pop("profile", None)
            self.credentials = self.credential_store.get_credentials(self.credential_profile_name)

        self.session = Connection(self.credentials)

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

        if method in ("POST", "PUT"):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
                raw_data = kwargs.pop("data", {})
                raw_data = json.dumps(raw_data, sort_keys=True)

        return self.session.http_request(method, uri, headers=headers, data=raw_data, **kwargs)

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
        if unique_id:
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
