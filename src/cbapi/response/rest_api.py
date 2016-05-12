#!/usr/bin/env python

from __future__ import absolute_import

import json

from six.moves import urllib

from distutils.version import LooseVersion
from ..connection import BaseAPI
from .models import Process, Binary
from ..errors import UnauthorizedError, ApiError, MoreThanOneResultError
from ..utils import convert_query_params
from ..query import PaginatedQuery
from ..errors import CredentialError

import requests

import logging

log = logging.getLogger(__name__)


def get_api_token(base_url, username, password, **kwargs):
    """Retrieve the API token for a user given the URL of the server, username, and password.

    :param str: base_url: The URL of the server (for example, ``https://carbonblack.server.com``)
    :param str: username: The user's username
    :param str: password: The user's password
    :param bool: verify: (optional) When set to False, turn off SSL certificate verification

    :return: The user's API token
    :rtype: str
    :raises ApiError: if there is an error parsing the reply
    :raises CredentialError: if the username/password is incorrect
    """
    r = requests.get("{0:s}/api/auth".format(base_url), auth=requests.auth.HTTPDigestAuth(username, password), **kwargs)
    if r.status_code != 200:
        raise CredentialError(message="Invalid credentials: {0:s}".format(r.content))

    try:
        return r.json()["auth_token"]
    except:
        raise ApiError(message="Error retrieving auth_token: {0:s}".format(r.content))


class CbEnterpriseResponseAPI(BaseAPI):
    """The main entry point into the Carbon Black Enterprise Response API.
    Note that calling this will automatically connect to the Carbon Black server in order to verify
    connectivity and get the server version.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server. Uses the
        profile named 'default' when not specified.

    Usage::

    >>> from cbapi import CbEnterpriseResponseAPI
    >>> cb = CbEnterpriseResponseAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbEnterpriseResponseAPI, self).__init__(product_name="response", *args, **kwargs)

        self._parsed_url = urllib.parse.urlparse(self.url)
        try:
            server_info = self.info()
        except UnauthorizedError:
            raise UnauthorizedError(uri=self.url, message="Invalid API token for server {0:s}.".format(self.url))

        log.debug('Connected to Cb server version %s at %s' % (server_info['version'], self.session.server))
        self.cb_server_version = LooseVersion(server_info['version'])
        if self.cb_server_version < LooseVersion('5.0'):
            raise ApiError("CbEnterpriseResponseAPI only supports Cb servers version >= 5.0.0")

    def info(self):
        """Retrieve basic version information from the Carbon Black Enterprise Response server.

        :return: Dictionary with information retrieved from the ``/api/info`` API route
        :rtype: dict
        """
        r = self.session.get("/api/info")
        return r.json()

    def license_request(self):
        """Retrieve license request block from the Carbon Black Enterprise Response server.

        :return: License request block
        :rtype: str
        """
        r = self.session.get("/api/license")
        return r.json().get("license_request_block", "")

    def update_license(self, license_block):
        """Upload new license to the Carbon Black Enterprise Response server.

        :param str license_block: Licence block provided by Carbon Black support
        :raises ServerError: if the license is not accepted by the Carbon Black server
        """
        r = self.session.post("/api/license", data=json.dumps({"license": license_block}))
        self.raise_unless_json(r, {"status": "success"})

    def _perform_query(self, cls, **kwargs):
        if hasattr(cls, "_query_implementation"):
            return cls._query_implementation(self)
        else:
            return Query(cls, self, **kwargs)

    def from_ui(self, uri):
        """Retrieve a Carbon Black Enterprise Response object based on URL from the Carbon Black Enterprise Response
        web user interface.

        For example, calling this function with
        ``https://server/#/analyze/00000001-0000-0554-01d1-3bc4553b8c9f/1`` as the ``uri`` argument will return a new
        :py:class: cbapi.response.models.Process class initialized with the process GUID from the URL.

        :param str uri: Web browser URL from the Cb web interface
        :return: the appropriate model object for the URL provided
        :raises ApiError: if the URL does not correspond to a recognized model object
        """
        o = urllib.parse.urlparse(uri)
        if self._parsed_url.scheme != o.scheme or \
                        self._parsed_url.hostname != o.hostname or \
                        self._parsed_url.port != o.port:
            raise ApiError("Invalid URL provided")

        frag = o.fragment.lstrip('/')
        if frag.startswith('analyze'):
            (analyze, procid, segment) = frag.split('/')[:3]
            return self.select(Process, procid, int(segment))
        elif frag.startswith('binary'):
            (binary, md5) = frag.split('/')[:2]
            return self.select(Binary, md5)
        elif frag.startswith('login') or not o.fragment:
            return self
        else:
            raise ApiError("Unknown URL endpoint: %s" % uri)


class Query(PaginatedQuery):
    """Represents a prepared query to the Carbon Black Enterprise Response server.

    This object is returned as part of a :py:meth:`CbEnterpriseResponseAPI.select`
    operation on Process and Binary objects from the Carbon Black
    Enterprise Response server. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    The syntax for query :py:meth:where and :py:meth:sort methods can be found in the
    `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_ posted on the Carbon Black
    Developer Network website.

    Examples::

    >>> cb = CbEnterpriseResponseAPI()
    >>> query = cb.select(Process)                      # returns a Query object matching all Processes
    >>> query = query.where("process_name:notepad.exe") # add a filter to this Query
    >>> query = query.sort("last_update desc")          # sort by last update time, most recent first
    >>> for proc in query:                              # uses the iterator to retrieve all results
    >>>     print proc.username, proc.hostname
    >>> processes = proc[:10]                           # retrieve the first ten results
    >>> len(processes)                                  # retrieve the total count

    Notes:
        - The slicing operator only supports start and end parameters, but not step. ``[1:-1]`` is legal, but
          ``[1:2:-1]`` is not.
        - You can chain where clauses together to create AND queries; only objects that match all ``where`` clauses
          will be returned.
    """
    def __init__(self, doc_class, cb, query=None, raw_query=None):
        super(Query, self).__init__(doc_class, cb, query=query)

        if raw_query:
            self.raw_query = urllib.parse.parse_qs(raw_query)
        else:
            self.raw_query = None

        self.sort_by = getattr(self.doc_class, 'default_sort', None)
        self._default_args = {"cb.urlver": 1, 'facet': 'false'}

    def sort(self, new_sort):
        """Set the sort order for this query.

        :param str new_sort: New sort order - see the `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        new_sort = new_sort.strip()
        if len(new_sort) == 0:
            self.sort_by = None
        else:
            self.sort_by = new_sort
        return self

    def and_(self, new_query):
        """Add a filter to this query. Equivalent to calling :py:meth:`where` on this object.

        :param str new_query: Query string - see the `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        return self.where(new_query)

    def where(self, new_query):
        """Add a filter to this query.

        :param str new_query: Query string - see the `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if self.raw_query:
            raise ApiError("Cannot call .where() on a raw query")

        if self.query and len(self.query) > 0:
            self.query = "{0:s} {1:s}".format(self.query, new_query)
        else:
            self.query = new_query

        return self

    def facets(self, *args):
        """Retrieve a dictionary with the facets for this query.

        :param args: Any number of fields to use as facets
        :return: Facet data
        :rtype: dict
        """
        # TODO: make this interface better
        qargs = self._default_args.copy()
        qargs['facet'] = 'true'
        qargs['start'] = 0
        qargs['rows'] = 0
        qargs['facet.field'] = list(args)

        if self.query:
            qargs['q'] = self.query

        query_params = convert_query_params(qargs)
        return self.cb.get_object(self.doc_class.urlobject, query_parameters=query_params).get('facets', {})

    def _count(self):
        if self.count_valid:
            return self.total_results

        if self.raw_query:
            args = self.raw_query.copy()
        else:
            args = self._default_args.copy()
            if self.query:
                args['q'] = self.query

        args['start'] = 0
        args['rows'] = 0

        qargs = convert_query_params(args)

        self.total_results = self.cb.get_object(self.doc_class.urlobject, query_parameters=qargs).get('total_results', 0)

        self.count_valid = True
        return self.total_results

    def _search(self, start=0, rows=0, perpage=100):
        # iterate over total result set, 100 at a time

        if self.raw_query:
            args = self.raw_query.copy()
        else:
            args = self._default_args.copy()
            args['start'] = start

            if self.query:
                args['q'] = self.query
            else:
                args['q'] = ''

        if self.sort_by:
            args['sort'] = self.sort_by
        if rows:
            args['rows'] = min(rows, perpage)
        else:
            args['rows'] = perpage

        still_querying = True
        current = start
        numrows = 0

        while still_querying:
            qargs = convert_query_params(args)
            result = self.cb.get_object(self.doc_class.urlobject, query_parameters=qargs)

            self.total_results = result.get('total_results')
            self.count_valid = True

            for item in result.get('results'):
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current

            if current >= self.total_results:
                break
