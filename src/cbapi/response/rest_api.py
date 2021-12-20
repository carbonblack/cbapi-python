#!/usr/bin/env python

from __future__ import absolute_import

from cbapi.six.moves import urllib

from distutils.version import LooseVersion
from ..connection import BaseAPI
from .models import Process, Binary, Watchlist, Investigation, Alert, ThreatReport, StoragePartition
from ..errors import UnauthorizedError, ApiError, ClientError
from .cblr import LiveResponseSessionManager
from .query import Query


import logging
log = logging.getLogger(__name__)


class CbResponseAPI(BaseAPI):
    """The main entry point into the Carbon Black EDR API.
    Note that calling this will automatically connect to the Carbon Black server in order to verify
    connectivity and get the server version.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black
        server. Uses the profile named 'default' when not specified.
    :param str url: (optional, discouraged) Instead of using a credential profile, pass URL and API token to
        the constructor.
    :param str token: (optional, discouraged) API token
    :param bool ssl_verify: (optional, discouraged) Enable or disable SSL certificate verification

    Usage::

    >>> from cbapi import CbResponseAPI
    >>> cb = CbResponseAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        timeout = kwargs.pop("timeout", 120)   # set default timeout period to two minutes, 2x the default nginx timeout
        super(CbResponseAPI, self).__init__(product_name="response", timeout=timeout, *args, **kwargs)

        self._parsed_url = urllib.parse.urlparse(self.url)
        try:
            self.server_info = self.info()
        except UnauthorizedError:
            raise UnauthorizedError(uri=self.url, message="Invalid API token for server {0:s}.".format(self.url))

        log.debug('Connected to Cb server version %s at %s' % (self.server_info['version'], self.session.server))
        self.cb_server_version = LooseVersion(self.server_info['version'])
        if self.cb_server_version < LooseVersion('5.0'):
            raise ApiError("CbEnterpriseResponseAPI only supports Cb servers version >= 5.0.0")

        self._has_legacy_partitions = False
        try:
            if self.cb_server_version >= LooseVersion('6.0'):
                legacy_partitions = [p for p in self.select(StoragePartition) if p.info.get("isLegacy", False)]
                if legacy_partitions:
                    self._has_legacy_partitions = True
        except ClientError as ce:
            # If we get a 403 on this endpoint, ignore during init,
            # as we will not be able to work with StoragePartitions regardless
            # https://github.com/carbonblack/cbapi-python/issues/303
            if ce.error_code == 403:
                pass
            else:
                raise ce  # no intervention

        self._lr_scheduler = None

    @property
    def live_response(self):
        if self._lr_scheduler is None:
            if not self.server_info.get("cblrEnabled", False):
                raise ApiError("Cb server does not support Live Response")
            self._lr_scheduler = LiveResponseSessionManager(self)

        return self._lr_scheduler

    def info(self):
        """Retrieve basic version information from the Carbon Black DER server.

        :return: Dictionary with information retrieved from the ``/api/info`` API route
        :rtype: dict
        """
        r = self.session.get("/api/info")
        return r.json()

    def dashboard_statistics(self):
        """Retrieve dashboard statistics from the Carbon Black EDR server.

        :return: Dictionary with information retrieved from the ``/api/v1/dashboard/statistics`` API route
        :rtype: dict
        """
        r = self.session.get("/api/v1/dashboard/statistics")
        return r.json()

    def license_request(self):
        """Retrieve license request block from the Carbon Black EDR server.

        :return: License request block
        :rtype: str
        """
        r = self.session.get("/api/license")
        return r.json().get("license_request_block", "")

    def update_license(self, license_block):
        """Upload new license to the Carbon Black EDR server.

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
        """Retrieve a Carbon Black EDR object based on URL from the Carbon Black EDR web user interface.

        For example, calling this function with
        ``https://server/#/analyze/00000001-0000-0554-01d1-3bc4553b8c9f/1`` as the ``uri`` argument will return a new
        :py:class: cbapi.response.models.Process class initialized with the process GUID from the URL.

        :param str uri: Web browser URL from the CB web interface
        :return: the appropriate model object for the URL provided
        :raises ApiError: if the URL does not correspond to a recognized model object
        """
        o = urllib.parse.urlparse(uri)
        if self._parsed_url.scheme != o.scheme \
            or self._parsed_url.hostname != o.hostname \
                or self._parsed_url.port != o.port:
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

    def create_new_partition(self):
        """Create a new Solr time partition for event storage. Available in Carbon Black EDR 6.1 and above.
        This will force roll-over current hot partition into warm partition (by renaming it to a time-stamped name)
        and create a new hot partition ("writer").

        :returns: Nothing if successful.
        :raises ApiError: if there was an error creating the new partition.
        :raises ServerError: if there was an error creating the new partition.
        """
        self.post_object("/api/v1/storage/events/new_partition", None)


class CbEnterpriseResponseAPI(CbResponseAPI):
    """
    Backwards compatibility for previous scripts
    """
    pass
