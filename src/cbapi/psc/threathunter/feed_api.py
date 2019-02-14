from cbapi.connection import BaseAPI
from cbapi.errors import ApiError
import logging
log = logging.getLogger(__name__)


class CbThreatHunterFeedAPI(BaseAPI):
    """The main entry point into the Cb ThreatHunter PSC Feed API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi.psc.threathunter import CbThreatHunterFeedAPI
    >>> cb = CbThreatHunterFeedAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbThreatHunterFeedAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

    def _perform_query(self, cls, **kwargs):
        return cls._query_implementation(self)

    def create(self, cls, data=None):
        # NOTE(ww): This doesn't work, since NewBaseModel.__setattr__ prevents
        # modification of non-underscore fields.
        # obj = super(CbThreatHunterFeedAPI, self).create(cls, data)

        obj = cls(self, initial_data=data)

        if hasattr(obj, "_create"):
            return obj._create()
        return obj

    def validate_query(self, query):
        args = {"q": query}
        resp = self.get_object("/pscr/query/v1/events/validate", query_parameters=args)

        return resp.get("valid", False)
