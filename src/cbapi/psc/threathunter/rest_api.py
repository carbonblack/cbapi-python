from cbapi.psc.threathunter.query import Query
from cbapi.connection import BaseAPI
import logging
import time

log = logging.getLogger(__name__)

#
# TODO: change base api_json_request to respect `error_code` and `message` from the response to create useful error messages.


class CbThreatHunterAPI(BaseAPI):
    """The main entry point into the Cb Response PSC API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi.psc.threathunter import CbThreatHunterAPI
    >>> cb = CbThreatHunterAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbThreatHunterAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

    def _perform_query(self, cls, **kwargs):
        if hasattr(cls, "_query_implementation"):
            return cls._query_implementation(self)
        else:
            return Query(cls, self, **kwargs)
