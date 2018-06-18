from cbapi.psc.response.query import Query
from cbapi.connection import BaseAPI
import logging
import time

log = logging.getLogger(__name__)


class CbResponseAPI(BaseAPI):
    """The main entry point into the Cb Response PSC API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi.psc.response import CbResponseAPI
    >>> cb = CbResponseAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbResponseAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

    def _perform_query(self, cls, **kwargs):
        if hasattr(cls, "_query_implementation"):
            return cls._query_implementation(self)
        else:
            return Query(cls, self, **kwargs)

    def notification_listener(self, interval=60):
        """Generator to continually poll the Cb Defense server for notifications (alerts). Note that this can only
        be used with a 'SIEM' key generated in the Cb Defense console.
        """
        while True:
            for notification in self.get_notifications():
                yield notification
            time.sleep(interval)

    def get_notifications(self):
        """Retrieve queued notifications (alerts) from the Cb Defense server. Note that this can only be used
        with a 'SIEM' key generated in the Cb Defense console.

        :returns: list of dictionary objects representing the notifications, or an empty list if none available.
        """
        res = self.get_object("/integrationServices/v3/notification")
        return res.get("notifications", [])

    @property
    def live_response(self):
        if self._lr_scheduler is None:
            self._lr_scheduler = LiveResponseSessionManager(self)

        return self._lr_scheduler

    def _request_lr_session(self, sensor_id):
        return self.live_response.request_session(sensor_id)


