from cbapi.psc.threathunter.query import Query
from cbapi.psc.rest_api import CbPSCBaseAPI
from cbapi.psc.threathunter.models import ReportSeverity
from cbapi.errors import CredentialError
import logging

log = logging.getLogger(__name__)


class CbThreatHunterAPI(CbPSCBaseAPI):
    """The main entry point into the Carbon Black Cloud Enterprise EDR API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi.psc.threathunter import CbThreatHunterAPI
    >>> cb = CbThreatHunterAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbThreatHunterAPI, self).__init__(*args, **kwargs)

        if not self.credentials.get("org_key", None):
            raise CredentialError("No organization key specified")

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
        url = "/threathunter/search/v1/orgs/{}/processes/search_validation".format(
            self.credentials.org_key
        )
        resp = self.get_object(url, query_parameters=args)

        return resp.get("valid", False)

    def convert_query(self, query):
        """Converts a legacy Carbon Black EDR query to an Enterprise EDR query.

        :param str query: the query to convert
        :return: the converted query
        :rtype: str
        """
        args = {"query": query}
        resp = self.post_object("/threathunter/feedmgr/v2/query/translate", args).json()

        return resp.get("query")

    @property
    def custom_severities(self):
        """Returns a list of active :py:class:`ReportSeverity` instances

        :rtype: list[:py:class:`ReportSeverity`]
        """
        # TODO(ww): There's probably a better place to put this.
        url = "/threathunter/watchlistmgr/v3/orgs/{}/reports/severity".format(
            self.credentials.org_key
        )
        resp = self.get_object(url)
        items = resp.get("results", [])
        return [self.create(ReportSeverity, item) for item in items]

    def queries(self):
        """Retrieves a list of queries, active or complete, known by
        the Enterprise EDR server.

        :return: a list of query ids
        :rtype: list(str)
        """
        url = "/threathunter/search/v1/orgs/{}/processes/search_jobs".format(
            self.credentials.org_key
        )
        ids = self.get_object(url)
        return ids.get("query_ids", [])

    def limits(self):
        """Returns a dictionary containing API limiting information.

        Example:

        >>> cb.limits()
        {u'status_code': 200, u'time_bounds': {u'upper': 1545335070095, u'lower': 1542779216139}}

        :return: a dict of limiting information
        :rtype: dict(str, str)
        """
        url = "/threathunter/search/v1/orgs/{}/processes/limits".format(
            self.credentials.org_key
        )
        return self.get_object(url)
