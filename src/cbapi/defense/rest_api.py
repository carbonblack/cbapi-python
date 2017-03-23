from ..utils import convert_query_params
from ..query import PaginatedQuery

from cbapi.connection import BaseAPI
import logging

log = logging.getLogger(__name__)


class CbDefenseAPI(BaseAPI):
    """The main entry point into the Cb Defense API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi import CbDefenseAPI
    >>> cb = CbDefenseAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbDefenseAPI, self).__init__(product_name="defense", *args, **kwargs)

    def _perform_query(self, cls, query_string=None):
        return Query(cls, self, query_string)


class Query(PaginatedQuery):
    """Represents a prepared query to the Cb Defense server.

    This object is returned as part of a :py:meth:`CbDefenseAPI.select`
    operation on models requested from the Cb Defense server. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    Examples::

    >>> from cbapi.defense import CbDefenseAPI
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

        :param str q: Query string - see the Enterprise Protection API reference <http://developer.carbonblack.com/reference/enterprise-protection/7.2/rest-api/#searching:ec3e4958451e5256ed16afd222059e6d>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        nq = self._clone()
        nq._query.append(q)
        return nq

    def and_(self, q):
        """Add a filter to this query. Equivalent to calling :py:meth:`where` on this object.

        :param str q: Query string - see the Enterprise Protection API reference <http://developer.carbonblack.com/reference/enterprise-protection/7.2/rest-api/#searching:ec3e4958451e5256ed16afd222059e6d>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        return self.where(q)

    def _count(self):
        # TODO: FIX
        args = {'limit': -1}
        if self._query:
            args['q'] = self._query

        query_args = convert_query_params(args)
        self._total_results = int(self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args).get("count", 0))
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

        if self._query:
            args['q'] = self._query

        still_querying = True

        while still_querying:
            query_args = convert_query_params(args)
            result = self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)

            self._total_results = result.get("totalResults", 0)
            self._count_valid = True

            for item in result.get("results", []):
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current + 1

            if len(result) < self._batch_size:
                break
