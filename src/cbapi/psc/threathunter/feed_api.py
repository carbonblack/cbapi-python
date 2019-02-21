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
    >>> from cbapi.psc.threathunter.models import Feed
    >>> cb = CbThreatHunterFeedAPI(profile="production")
    >>> for feed in cb.select(Feed):
    >>>    print(feed.name)
    """
    def __init__(self, *args, **kwargs):
        super(CbThreatHunterFeedAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

    def _perform_query(self, cls, **kwargs):
        return cls._query_implementation(self)

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
