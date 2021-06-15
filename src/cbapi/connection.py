#!/usr/bin/env python

"""Manages the CBAPI connection to the server."""

from __future__ import absolute_import

import requests
import sys
from requests.adapters import HTTPAdapter, DEFAULT_POOLBLOCK, DEFAULT_RETRIES, DEFAULT_POOLSIZE, DEFAULT_POOL_TIMEOUT

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

import logging
import json

from cbapi.six import iteritems
from cbapi.six.moves import urllib

from .auth import CredentialStoreFactory, Credentials
from .errors import ClientError, QuerySyntaxError, ServerError, TimeoutError, ApiError, ObjectNotFoundError, \
    UnauthorizedError, ConnectionError
from . import __version__

from .cache.lru import lru_cache_function
from .models import CreatableModelMixin
from .utils import calculate_elapsed_time, convert_query_params

log = logging.getLogger(__name__)


def try_json(resp):
    """
    Return a parsed JSON representation of the input.

    Args:
        resp (str): Input to be parsed.

    Returns:
        object: The parsed JSON result, or an empty dict if the value is not valid JSON.
    """
    try:
        return resp.json()
    except ValueError:
        return dict()


def check_python_tls_compatibility():
    """
    Verify which level of TLS/SSL that this version of the code is compatible with.

    Returns:
        str: The maximum level of TLS/SSL that this version is compatible with.
    """
    try:
        CbAPISessionAdapter(force_tls_1_2=True)
    except Exception:
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
    """Adapter object used to handle TLS connections to the CB server."""

    def __init__(self, verify_hostname=True, force_tls_1_2=False, max_retries=DEFAULT_RETRIES, **pool_kwargs):
        """
        Initialize the CbAPISessionManager.

        Args:
            verify_hostname (boolean): True if we want to verify the hostname.
            force_tls_1_2 (boolean): True to force the use of TLS 1.2.
            max_retries (int): Maximum number of retries.
            **pool_kwargs: Additional arguments.

        Raises:
            ApiError: If the library versions are too old to force the use of TLS 1.2.
        """
        self._cbapi_verify_hostname = verify_hostname
        self._cbapi_force_tls_1_2 = force_tls_1_2

        if force_tls_1_2 and not REQUESTS_HAS_URLLIB_SSL_CONTEXT:
            raise ApiError("Cannot force the use of TLS1.2: Python, urllib3, and requests versions are too old.")

        super(CbAPISessionAdapter, self).__init__(max_retries=max_retries, **pool_kwargs)

    def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs):
        """
        Initialize the connection pool manager.

        Args:
            connections (int): Initial number of connections to be used.
            maxsize (int): Maximum size of the connection pool.
            block (object): Blocking policy.
            **pool_kwargs: Additional arguments for the connection pool.

        Returns:
            object: TBD
        """
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
    """Object that encapsulates the HTTP connection to the CB server."""

    def __init__(self, credentials, integration_name=None, timeout=None, max_retries=None, proxy_session=None, **pool_kwargs):
        """
        Initialize the Connection object.

        Args:
            credentials (object): The credentials to use for the connection.
            integration_name (str): The integration name being used.
            timeout (int): The timeout value to use for HTTP requests on this connection.
            max_retries (int): The maximum number of times to retry a request.
            proxy_session (requests.Session) custom session to be used
            **pool_kwargs: Additional arguments to be used to initialize connection pooling.

        Raises:
            ApiError: If there's an internal error initializing the connection.
            ConnectionError: If there's a problem with the credentials.
        """
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

        user_agent = "cbapi/{0:s} Python/{1:d}.{2:d}.{3:d}" \
            .format(__version__, sys.version_info[0], sys.version_info[1], sys.version_info[2])
        if integration_name:
            user_agent += " {}".format(integration_name)

        self.token = credentials.token
        self.token_header = {'X-Auth-Token': self.token, 'User-Agent': user_agent}
        if proxy_session:
            self.session = proxy_session
            credentials.use_custom_proxy_session = True
        else:
            self.session = requests.Session()
            credentials.use_custom_proxy_session = False

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
        if credentials.use_custom_proxy_session:
            # get the custom session proxies
            self.proxies = self.session.proxies
        elif credentials.ignore_system_proxy:           # see https://github.com/kennethreitz/requests/issues/879
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
        """
        Submit a HTTP request to the server.

        Args:
            method (str): The method name to use for the HTTP request.
            url (str): The URL to submit the request to.
            **kwargs: Additional arguments for the request.

        Returns:
            object: Result of the HTTP request.

        Raises:
            ApiError: An unknown problem was detected.
            ClientError: The server returned an error code in the 4xx range, indicating a problem with the request.
            ConnectionError: A problem was seen with the HTTP connection.
            ObjectNotFoundError: The specified object was not found on the server.
            QuerySyntaxError: The query passed in had invalid syntax.
            ServerError: The server returned an error code in the 5xx range, indicating a problem on the server side.
            TimeoutError: The HTTP request timed out.
            UnauthorizedError: The stored credentials do not permit access to the specified request.
        """
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
            raise ConnectionError("Received a network connection error from {0:s}: {1:s}"
                                  .format(self.server, str(connection_error)),
                                  original_exception=connection_error)
        except Exception as e:
            raise ApiError("Unknown exception when connecting to server: {0:s}".format(str(e)),
                           original_exception=e)
        else:
            if r.status_code >= 500:
                raise ServerError(error_code=r.status_code, message=r.text)
            elif r.status_code == 404:
                raise ObjectNotFoundError(uri=uri, message=r.text)
            elif r.status_code == 401:
                raise UnauthorizedError(uri=uri, action=method, message=r.text)
            elif r.status_code == 400 and try_json(r).get('reason') == 'query_malformed_syntax':
                raise QuerySyntaxError(uri=uri, message=r.text)
            elif r.status_code >= 400:
                raise ClientError(error_code=r.status_code, message=r.text)
            return r

    def get(self, url, **kwargs):
        """
        Submit a GET request on this connection.

        Args:
            url (str): The URL to submit the request to.
            **kwargs: Additional arguments for the request.

        Returns:
            object: Result of the HTTP request.
        """
        return self.http_request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        """
        Submit a POST request on this connection.

        Args:
            url (str): The URL to submit the request to.
            **kwargs: Additional arguments for the request.

        Returns:
            object: Result of the HTTP request.
        """
        return self.http_request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        """
        Submit a PUT request on this connection.

        Args:
            url (str): The URL to submit the request to.
            **kwargs: Additional arguments for the request.

        Returns:
            object: Result of the HTTP request.
        """
        return self.http_request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        """
        Submit a DELETE request on this connection.

        Args:
            url (str): The URL to submit the request to.
            **kwargs: Additional arguments for the request.

        Returns:
            object: Result of the HTTP request.
        """
        return self.http_request("DELETE", url, **kwargs)


class BaseAPI(object):
    """The base API object used by all CBAPI objects to communicate with the server."""

    def __init__(self, *args, **kwargs):
        """
        Initialize the base API information.

        Args:
            *args: TBD
            **kwargs: Additional arguments.
        """
        product_name = kwargs.pop("product_name", None)
        credential_file = kwargs.pop("credential_file", None)
        integration_name = kwargs.pop("integration_name", None)
        self.credential_store = CredentialStoreFactory.getCredentialStore(product_name, credential_file)

        url, token, org_key = kwargs.pop("url", None), kwargs.pop("token", None), kwargs.pop("org_key", None)
        if url and token:
            if org_key:
                credentials = {"url": url, "token": token, "org_key": org_key}
            else:
                credentials = {"url": url, "token": token}

            for k in ("ssl_verify", "proxy", "ssl_cert_file"):
                if k in kwargs:
                    credentials[k] = kwargs.pop(k)
            self.credentials = Credentials(credentials)
            self.credential_profile_name = None
        else:
            self.credential_profile_name = kwargs.pop("profile", None)
            self.credentials = self.credential_store.get_credentials(self.credential_profile_name)

        timeout = kwargs.pop("timeout", DEFAULT_POOL_TIMEOUT)
        max_retries = kwargs.pop("max_retries", DEFAULT_RETRIES)
        proxy_session = kwargs.pop("proxy_session", None)
        pool_connections = kwargs.pop("pool_connections", 1)
        pool_maxsize = kwargs.pop("pool_maxsize", DEFAULT_POOLSIZE)
        pool_block = kwargs.pop("pool_block", DEFAULT_POOLBLOCK)

        self.session = Connection(self.credentials, integration_name=integration_name, timeout=timeout,
                                  max_retries=max_retries, proxy_session=proxy_session, pool_connections=pool_connections,
                                  pool_maxsize=pool_maxsize, pool_block=pool_block)

    def raise_unless_json(self, ret, expected):
        """
        Raise a ServerError unless we got back an HTTP 200 response with JSON containing all the expected values.

        Args:
            ret (object): Return value to be checked.
            expected (dict): Expected keys and values that need to be found in the JSON response.

        Raises:
            ServerError: If the HTTP response is anything but 200, or if the expected values are not found.
        """
        if ret.status_code == 200:
            message = ret.json()
            for k, v in iteritems(expected):
                if k not in message or message[k] != v:
                    raise ServerError(ret.status_code, message)
        else:
            raise ServerError(ret.status_code, "{0}".format(ret.content), )

    def get_object(self, uri, query_parameters=None, default=None):
        """
        Submit a GET request to the server and parse the result as JSON before returning.

        Args:
            uri (str): The URI to send the GET request to.
            query_parameters (object): Parameters for the query.
            default (object): What gets returned in the event of an empty response.

        Returns:
            object: Result of the GET request.
        """
        if query_parameters:
            if isinstance(query_parameters, dict):
                query_parameters = convert_query_params(query_parameters)
            uri += '?%s' % (urllib.parse.urlencode(sorted(query_parameters)))

        result = self.api_json_request("GET", uri)
        if result.status_code == 200:
            try:
                return result.json()
            except Exception:
                raise ServerError(result.status_code, "Cannot parse response as JSON: {0:s}".format(result.content))
        elif result.status_code == 204:
            # empty response
            return default
        else:
            raise ServerError(error_code=result.status_code, message="Unknown error: {0}".format(result.content))

    def get_raw_data(self, uri, query_parameters=None, default=None, **kwargs):
        """
        Submit a GET request to the server and return the result without parsing it.

        Args:
            uri (str): The URI to send the GET request to.
            query_parameters (object): Parameters for the query.
            default (object): What gets returned in the event of an empty response.
            **kwargs:

        Returns:
            object: Result of the GET request.
        """
        if query_parameters:
            if isinstance(query_parameters, dict):
                query_parameters = convert_query_params(query_parameters)
            uri += '?%s' % (urllib.parse.urlencode(sorted(query_parameters)))

        hdrs = kwargs.pop("headers", {})
        result = self.api_json_request("GET", uri, headers=hdrs)
        if result.status_code == 200:
            return result.text
        elif result.status_code == 204:
            # empty response
            return default
        else:
            raise ServerError(error_code=result.status_code, message="Unknown error: {0}".format(result.content))

    def api_json_request(self, method, uri, **kwargs):
        """
        Submit a request to the server.

        Args:
            method (str): HTTP method to use.
            uri (str): URI to submit the request to.
            **kwargs (dict): Additional arguments.

        Returns:
            object: Result of the operation.

        Raises:
             ServerError: If there's an error output from the server.
        """
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
        except ValueError:
            return result

        if "errorMessage" in resp:
            raise ServerError(error_code=result.status_code, message=resp["errorMessage"])

        return result

    def post_object(self, uri, body, **kwargs):
        """
        Send a POST request to the specified URI.

        Args:
            uri (str): The URI to send the POST request to.
            body (object): The data to be sent in the body of the POST request.
            **kwargs:

        Returns:
            object: The return data from the POST request.
        """
        return self.api_json_request("POST", uri, data=body, **kwargs)

    def put_object(self, uri, body, **kwargs):
        """
        Send a PUT request to the specified URI.

        Args:
            uri (str): The URI to send the PUT request to.
            body (object): The data to be sent in the body of the PUT request.
            **kwargs:

        Returns:
            object: The return data from the PUT request.
        """
        return self.api_json_request("PUT", uri, data=body, **kwargs)

    def delete_object(self, uri):
        """
        Send a DELETE request to the specified URI.

        Args:
            uri (str): The URI to send the DELETE request to.

        Returns:
            object: The return data from the DELETE request.
        """
        return self.api_json_request("DELETE", uri)

    def select(self, cls, unique_id=None, *args, **kwargs):
        """
        Prepare a query against the Carbon Black data store.

        Args:
            cls (class): The Model class (for example, Computer, Process, Binary, FileInstance) to query
            unique_id (optional): The unique id of the object to retrieve, to retrieve a single object by ID
            *args:
            **kwargs:

        Returns:
            object: An instance of the Model class if a unique_id is provided, otherwise a Query object
        """
        if unique_id is not None:
            return select_instance(self, cls, unique_id, *args, **kwargs)
        else:
            return self._perform_query(cls, **kwargs)

    def create(self, cls, data=None):
        """
        Create a new object.

        Args:
            cls (class): The Model class (only some models can be created, for example, Feed, Notification, ...)
            data (object): The data used to initialize the new object

        Returns:
            Model: An empty instance of the model class.

        Raises:
            ApiError: If the Model cannot be created.
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
        """
        Return the connection URL.

        Returns:
            str: The connection URL.
        """
        return self.session.server


# by default, set expiration to 1 minute and max_size to 1k elements
# TODO: how does this interfere with mutable objects?
@lru_cache_function(max_size=1024, expiration=1*60)
def select_instance(api, cls, unique_id, *args, **kwargs):
    """
    Select a cached instance of an object.

    Args:
        api: TBD
        cls: TBD
        unique_id: TBD
        *args:
        **kwargs:

    Returns:
        TBD
    """
    return cls(api, unique_id, *args, **kwargs)
