from cbapi.utils import convert_query_params
from cbapi.query import PaginatedQuery

from cbapi.psc.rest_api import CbPSCBaseAPI
import logging
import time

log = logging.getLogger(__name__)


def convert_to_kv_pairs(q):
    k, v = q.split(':', 1)
    return k, v


class CbDefenseAPI(CbPSCBaseAPI):
    """The main entry point into the Carbon Black Cloud Endpoint Standard Defense API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi import CbDefenseAPI
    >>> cb = CbDefenseAPI(profile="production")
    """

    def __init__(self, *args, **kwargs):
        super(CbDefenseAPI, self).__init__(*args, **kwargs)

    def _perform_query(self, cls, query_string=None):
        return Query(cls, self, query_string)

    def notification_listener(self, interval=60):
        """Generator to continually poll the Cloud Endpoint Standard server for notifications (alerts). Note that
        this can only be used with a 'SIEM' key generated in the Carbon Black Cloud console.
        """
        while True:
            for notification in self.get_notifications():
                yield notification
            time.sleep(interval)

    def get_notifications(self):
        """Retrieve queued notifications (alerts) from the Cloud Endpoint Standard server. Note that this can only be
        used with a 'SIEM' key generated in the Carbon Black Cloud console.

        :returns: list of dictionary objects representing the notifications, or an empty list if none available.
        """
        res = self.get_object("/integrationServices/v3/notification")
        return res.get("notifications", [])

    def get_auditlogs(self):
        """Retrieve queued audit logs from the Carbon Black Cloud Endpoint Standard server.
            Note that this can only be used with a 'API' key generated in the CBC console.
        :returns: list of dictionary objects representing the audit logs, or an empty list if none available.
        """
        res = self.get_object("/integrationServices/v3/auditlogs")
        return res.get("notifications", [])


class Query(PaginatedQuery):
    """Represents a prepared query to the Cloud Endpoint Standard server.

    This object is returned as part of a :py:meth:`CbDefenseAPI.select`
    operation on models requested from the Cloud Endpoint Standard server. You should not have to create
    this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    Examples::

    >>> from cbapi.psc.defense import CbDefenseAPI
    >>> cb = CbDefenseAPI()

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

    def prepare_query(self, args):
        if self._query:
            for qe in self._query:
                k, v = convert_to_kv_pairs(qe)
                args[k] = v

        return args

    def _count(self):
        args = {'limit': 0}
        args = self.prepare_query(args)

        query_args = convert_query_params(args)
        self._total_results = int(self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)
                                  .get("totalResults", 0))
        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = {}
        if start != 0:
            args['start'] = start
        args['rows'] = self._batch_size

        current = start
        numrows = 0

        args = self.prepare_query(args)
        still_querying = True

        while still_querying:
            query_args = convert_query_params(args)
            result = self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)

            self._total_results = result.get("totalResults", 0)
            self._count_valid = True

            results = result.get('results', [])

            if results is None:
                log.debug("Results are None")
                if current >= 100000:
                    log.info("Max result size exceeded. Truncated to 100k.")
                break

            for item in results:
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current + 1  # as of 6/2017, the indexing on the Cb Defense backend is still 1-based

            if current >= self._total_results:
                break

            if not results:
                log.debug("server reported total_results overestimated the number of results for this query by {0}"
                          .format(self._total_results - current))
                log.debug("resetting total_results for this query to {0}".format(current))
                self._total_results = current
                break
