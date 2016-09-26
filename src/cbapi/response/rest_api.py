#!/usr/bin/env python

from __future__ import absolute_import

from six.moves import urllib

from distutils.version import LooseVersion
from ..connection import BaseAPI
from .models import Process, Binary, Watchlist, Investigation, Alert, ThreatReport
from ..errors import UnauthorizedError, ApiError
from ..utils import convert_query_params
from ..query import PaginatedQuery
from ..errors import CredentialError
from .live_response_api import LiveResponseScheduler

import requests

import logging
log = logging.getLogger(__name__)


def get_api_token(base_url, username, password, **kwargs):
    """Retrieve the API token for a user given the URL of the server, username, and password.

    :param str base_url: The URL of the server (for example, ``https://carbonblack.server.com``)
    :param str username: The user's username
    :param str password: The user's password
    :param bool verify: (optional) When set to False, turn off SSL certificate verification

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
            self.server_info = self.info()
        except UnauthorizedError:
            raise UnauthorizedError(uri=self.url, message="Invalid API token for server {0:s}.".format(self.url))

        log.debug('Connected to Cb server version %s at %s' % (self.server_info['version'], self.session.server))
        self.cb_server_version = LooseVersion(self.server_info['version'])
        if self.cb_server_version < LooseVersion('5.0'):
            raise ApiError("CbEnterpriseResponseAPI only supports Cb servers version >= 5.0.0")

        self._lr_scheduler = None

    @property
    def live_response(self):
        if self._lr_scheduler is None:
            if not self.server_info.get("cblrEnabled", False):
                raise ApiError("Cb server does not support Live Response")
            self._lr_scheduler = LiveResponseScheduler(self)

        return self._lr_scheduler

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
        r = self.post_object("/api/license", {"license": license_block})
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
        parts = frag.split('/')
        if len(parts) < 2:
            raise ApiError("URL endpoint does not include a unique ID: %s" % uri)

        if frag.startswith('analyze'):
            (analyze, procid, segment) = parts[:3]
            return self.select(Process, procid, int(segment))
        elif frag.startswith('binary'):
            (binary, md5) = parts[:2]
            return self.select(Binary, md5)
        elif frag.startswith('watchlist'):
            (watchlist, watchlist_id) = parts[:2]
            return self.select(Watchlist, watchlist_id)
        elif frag.startswith('search'):
            (search, raw_query) = parts[:2]
            return Query(Process, self, raw_query=raw_query)
        elif frag.startswith('binaries'):
            (binaries, raw_query) = parts[:2]
            return Query(Binary, self, raw_query=raw_query)
        elif frag.startswith('investigation'):
            (investigation, investigation_id) = parts[:2]
            return self.select(Investigation).where("id:{0:s}".format(investigation_id)).one()
        elif frag.startswith('alerts'):
            (alerts, raw_query) = parts[:2]
            return Query(Alert, self, raw_query=raw_query)
        elif frag.startswith('threats'):
            (threats, raw_query) = parts[:2]
            return Query(ThreatReport, self, raw_query=raw_query)
        elif frag.startswith('threat-details'):
            (threatdetails, feed_id, feed_title) = parts[:3]
            return self.select(ThreatReport, "%s:%s" % (feed_id, feed_title))
        elif frag.startswith('login') or not o.fragment:
            return self
        else:
            raise ApiError("Unknown URL endpoint: %s" % uri)

    def _request_lr_session(self, sensor_id):
        return self.live_response.request_session(sensor_id)

    def _close_lr_session(self, sensor_id):
        return self.live_response.close_session(sensor_id)


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
    >>>     print("{0} {1}".format(proc.username, proc.hostname))
    >>> processes = query[:10]                          # retrieve the first ten results
    >>> len(query)                                      # retrieve the total count

    Notes:
        - The slicing operator only supports start and end parameters, but not step. ``[1:-1]`` is legal, but
          ``[1:2:-1]`` is not.
        - You can chain where clauses together to create AND queries; only objects that match all ``where`` clauses
          will be returned.
    """
    def __init__(self, doc_class, cb, query=None, raw_query=None):
        super(Query, self).__init__(doc_class, cb, query=query)

        if raw_query:
            self._raw_query = urllib.parse.parse_qs(raw_query)
        else:
            self._raw_query = None

        self._sort_by = getattr(self._doc_class, 'default_sort', None)
        self._default_args = {"cb.urlver": 1, 'facet': 'false'}

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        nq._query = self._query
        nq._raw_query = None
        if self._raw_query:
            nq._raw_query = self._raw_query

        nq._sort_by = self._sort_by
        nq._default_args = self._default_args
        return nq

    def create_watchlist(self, watchlist_name):
        """Create a watchlist based on this query.

        :param str watchlist_name: name of the new watchlist
        :return: new Watchlist object
        :rtype: :py:class:`Watchlist`
        """
        if self._raw_query:
            args = self._raw_query.copy()
        else:
            args = self._default_args.copy()

            if self._query:
                args['q'] = self._query
            else:
                args['q'] = ''

        if self._sort_by:
            args['sort'] = self._sort_by

        new_watchlist = self._cb.create(Watchlist, data={"name": watchlist_name})
        new_watchlist.search_query = urllib.parse.urlencode(args)
        if self._doc_class == Binary:
            new_watchlist.index_type = "modules"
        else:
            new_watchlist.index_type = "events"

        return new_watchlist.save()

    def sort(self, new_sort):
        """Set the sort order for this query.

        :param str new_sort: New sort order - see the `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        new_sort = new_sort.strip()

        nq = self._clone()
        if len(new_sort) == 0:
            nq._sort_by = None
        else:
            nq._sort_by = new_sort
        return nq

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
        if self._raw_query:
            raise ApiError("Cannot call .where() on a raw query")

        nq = self._clone()
        if nq._query and len(nq._query) > 0:
            nq._query = "{0:s} {1:s}".format(self._query, new_query)
        else:
            nq._query = new_query

        return nq

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

        if self._query:
            qargs['q'] = self._query

        query_params = convert_query_params(qargs)
        return self._cb.get_object(self._doc_class.urlobject, query_parameters=query_params).get('facets', {})

    def _count(self):
        if self._count_valid:
            return self._total_results

        if self._raw_query:
            args = self._raw_query.copy()
        else:
            args = self._default_args.copy()
            if self._query:
                args['q'] = self._query

        args['start'] = 0
        args['rows'] = 0

        qargs = convert_query_params(args)

        self._total_results = self._cb.get_object(self._doc_class.urlobject, query_parameters=qargs).get('total_results', 0)

        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0, perpage=100):
        # iterate over total result set, 100 at a time

        if self._raw_query:
            args = self._raw_query.copy()
        else:
            args = self._default_args.copy()
            args['start'] = start

            if self._query:
                args['q'] = self._query
            else:
                args['q'] = ''

        if self._sort_by:
            args['sort'] = self._sort_by
        if rows:
            args['rows'] = min(rows, perpage)
        else:
            args['rows'] = perpage

        still_querying = True
        current = start
        numrows = 0

        while still_querying:
            qargs = convert_query_params(args)
            result = self._cb.get_object(self._doc_class.urlobject, query_parameters=qargs)

            self._total_results = result.get('total_results')
            self._count_valid = True

            for item in result.get('results'):
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current

            if current >= self._total_results:
                break
