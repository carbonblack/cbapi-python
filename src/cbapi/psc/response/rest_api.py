from cbapi.utils import convert_query_params
from cbapi.query import PaginatedQuery

from cbapi.connection import BaseAPI
import logging
import time

log = logging.getLogger(__name__)


def convert_to_kv_pairs(q):
    k, v = q.split(':', 1)
    return k, v


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


class Query(PaginatedQuery):
    """Represents a prepared query to the Cb Resposne PSC backend.

    This object is returned as part of a :py:meth:`CbResponseAPI.select`
    operation on models requested from the Cb Response PSC backend. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    Examples::

    >>> from cbapi.psc.response import CbResponseAPI
    >>> cb = CbResponseAPI()

    Notes:
        - The slicing operator only supports start and end parameters, but not step. ``[1:-1]`` is legal, but
          ``[1:2:-1]`` is not.
        - You can chain where clauses together to create AND queries; only objects that match all ``where`` clauses
          will be returned.
    """
    def __init__(self, doc_class, cb, query=None):
        super(Query, self).__init__(doc_class, cb, None)
        if query:
            self._query = [query]
        else:
            self._query = []

        self._sort_by = None
        self._group_by = None
        self._batch_size = 100
        self._raw_query = None
        self._default_args = {}

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        nq._query = self._query[::]
        nq._sort_by = self._sort_by
        nq._group_by = self._group_by
        nq._batch_size = self._batch_size
        return nq

    def where(self, q):
        """Add a filter to this query.

        :param str q: Query string
        :return: Query object
        :rtype: :py:class:`Query`
        """
        nq = self._clone()
        nq._query.append(q)
        return nq

    def and_(self, q):
        """Add a filter to this query. Equivalent to calling :py:meth:`where` on this object.

        :param str q: Query string
        :return: Query object
        :rtype: :py:class:`Query`
        """
        return self.where(q)

    def _get_query_parameters(self):
        if self._raw_query:
            args = self._raw_query.copy()
        else:
            args = self._default_args.copy()
            if self._query:
                args['q'] = self._query
            else:
                args['q'] = ''

        return args

    def _count(self):
        args = {'limit': 0}

        query_args = convert_query_params(args)
        self._total_results = int(self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)
                                  .get("totalResults", 0))
        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = self._get_query_parameters()
        if start != 0:
            args['start'] = start
        args['rows'] = self._batch_size

        current = start
        numrows = 0

        still_querying = True

        while still_querying:
            query_args = convert_query_params(args)
            result = self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)

            self._total_results = result.get("totalResults", 0)
            self._count_valid = True

            results = result.get('results', [])

            for item in results:
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current + 1     # as of 6/2017, the indexing on the Cb Defense backend is still 1-based

            if current >= self._total_results:
                break
            if not results:
                log.debug("server reported total_results overestimated the number of results for this query by {0}"
                          .format(self._total_results - current))
                log.debug("resetting total_results for this query to {0}".format(current))
                self._total_results = current
                break
