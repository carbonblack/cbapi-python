from cbapi.connection import BaseAPI
from .cblr import LiveResponseSessionManager
import logging

log = logging.getLogger(__name__)

class CbPSCBaseAPI(BaseAPI):
    """The main entry point into the Cb PSC API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi import CbPSCBaseAPI
    >>> cb = CbPSCBaseAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbPSCBaseAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

    @property
    def live_response(self):
        if self._lr_scheduler is None:
            self._lr_scheduler = LiveResponseSessionManager(self)
        return self._lr_scheduler

    def _request_lr_session(self, sensor_id):
        return self.live_response.request_session(sensor_id)
