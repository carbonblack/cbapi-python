from cbapi.psc.threathunter.query import Query
from cbapi.connection import BaseAPI
import logging

log = logging.getLogger(__name__)


class CbThreatHunterAPI(BaseAPI):
    """The main entry point into the Cb ThreatHunter PSC API.

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

    def queries(self):
        """Retrieves a list of queries, active or complete, known by
        the ThreatHunter server.

        :return: a list of query ids
        :rtype: list(str)
        """
        ids = self.get_object("/pscr/query/v1/list")
        return ids.get("query_ids", [])

    def limits(self):
        """Returns a dictionary containing API limiting information.

        Example:

        >>> cb.limits()
        {u'status_code': 200, u'time_bounds': {u'upper': 1545335070095, u'lower': 1542779216139}}

        :return: a dict of limiting information
        :rtype: dict(str, str)
        """
        return self.get_object("/pscr/query/v1/limits")
