from cbapi.psc.livequery.query import Query
from cbapi.psc.livequery.models import Result
from cbapi.connection import BaseAPI
from cbapi.errors import CredentialError
import logging

log = logging.getLogger(__name__)


class CbLiveQueryAPI(BaseAPI):
    def __init__(self, *args, **kwargs):
        super(CbLiveQueryAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

        if not self.credentials.get("org_key", None):
            raise CredentialError("No organization key specified")

    def _perform_query(self, cls, **kwargs):
        return Query(cls, self, **kwargs)

    def query(self, sql):
        return self.select(Result).where(sql=sql)
