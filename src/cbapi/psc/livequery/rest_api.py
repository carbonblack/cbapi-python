from cbapi.psc.livequery.models import Run
from cbapi.connection import BaseAPI
from cbapi.errors import CredentialError, ApiError
import logging

log = logging.getLogger(__name__)


class CbLiveQueryAPI(BaseAPI):
    """The main entry point into the Cb PSC LiveQuery API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi.psc.livequery import CbLiveQueryAPI
    >>> cb = CbLiveQueryAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbLiveQueryAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

        if not self.credentials.get("org_key", None):
            raise CredentialError("No organization key specified")

    def _perform_query(self, cls, **kwargs):
        if hasattr(cls, "_query_implementation"):
            return cls._query_implementation(self)
        else:
            raise ApiError("All LiveQuery models should provide _query_implementation")

    def query(self, sql):
        return self.select(Run).where(sql=sql)
