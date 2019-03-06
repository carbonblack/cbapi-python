from cbapi.psc.threathunter.query import Query
from cbapi.connection import BaseAPI
from cbapi.psc.threathunter.models import ReportSeverity
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

    def create(self, cls, data=None):
        """Creates a new model.

        >>> feed = cb.create(Feed, feed_data)

        :param cls: The model being created
        :param data: The data to pre-populate the model with
        :type data: dict(str, object)
        :return: an instance of `cls`
        """
        return cls(self, initial_data=data)

    def validate_query(self, query):
        """Validates the given IOC query.

        >>> cb.validate_query("process_name:chrome.exe") # True

        :param str query: the query to validate
        :return: whether or not the query is valid
        :rtype: bool
        """
        args = {"q": query}
        resp = self.get_object("/pscr/query/v1/validate", query_parameters=args)

        return resp.get("valid", False)

    def convert_query(self, query):
        """Converts a legacy CB Response query to a ThreatHunter query.

        :param str query: the query to convert
        :return: the converted query
        :rtype: str
        """
        args = {"query": query}
        resp = self.get_object("/threathunter/feedmgr/v1/query/translate", query_parameters=args)

        return resp.get("query")

    @property
    def custom_severities(self):
        """Returns a list of active :py:class:`ReportSeverity` instances

        :rtype: list[:py:class:`ReportSeverity`]
        """
        # TODO(ww): There's probably a better place to put this.
        resp = self.get_object("/threathunter/watchlistmgr/v1/severity")
        items = resp.get("results", [])
        return [self.create(ReportSeverity, item) for item in items]

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
