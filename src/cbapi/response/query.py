from ..utils import convert_query_params
from ..query import PaginatedQuery
from cbapi.six.moves import urllib
from distutils.version import LooseVersion
from ..errors import ApiError
import copy

import logging

log = logging.getLogger(__name__)


class Query(PaginatedQuery):
    """Represents a prepared query to the Carbon Black EDR server.

    This object is returned as part of a :py:meth:`CbResponseAPI.select`
    operation on Process and Binary objects from the Carbon Black
    EDR server. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    The syntax for query :py:meth:where and :py:meth:sort methods can be found in the
    `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_ posted on the Carbon Black
    Developer Network website.

    Examples::

    >>> cb = CbResponseAPI()
    >>> query = cb.select(Process)                      # returns a Query object matching all Processes
    >>> query = query.where("process_name:notepad.exe") # add a filter to this Query
    >>> query = query.sort("last_update desc")          # sort by last update time, most recent first
    >>> for proc in query:                              # uses the iterator to retrieve all results
    >>>     print("{0} {1}".format(proc.username, proc.hostname))
    >>> processes = query[:10]                          # retrieve the first ten results
    >>> len(query)                                      # retrieve the total count

    Notes:
        - The slicing operator only supports start and end parameters, but not step. ``[1:-1]`` is legal, but
          ``[1:2:-1]`` is not.
        - You can chain where clauses together to create AND queries; only objects that match all ``where`` clauses
          will be returned.
    """
    def __init__(self, doc_class, cb, query=None, raw_query=None):
        super(Query, self).__init__(doc_class, cb, query=query)

        if raw_query:
            self._raw_query = urllib.parse.parse_qs(raw_query)
        else:
            self._raw_query = None

        self._sort_by = getattr(self._doc_class, 'default_sort', None)
        self._default_args = {"cb.urlver": 1}

        # FIX: Cb Response server version 5.1.0-3 throws an exception after returning HTTP 504 when facet=false in the
        # HTTP request. Work around this by only setting facet=false on 5.1.1 and above server versions.
        if self._cb.cb_server_version >= LooseVersion('5.1.1'):
            self._default_args["facet"] = "false"

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        nq._query = self._query
        nq._raw_query = None
        if self._raw_query:
            nq._raw_query = self._raw_query

        nq._sort_by = self._sort_by
        nq._default_args = copy.deepcopy(self._default_args)
        nq._batch_size = self._batch_size
        return nq

    def sort(self, new_sort):
        """Set the sort order for this query.

        :param str new_sort: New sort order - see the
            `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        new_sort = new_sort.strip()

        nq = self._clone()
        if len(new_sort) == 0:
            nq._sort_by = None
        else:
            nq._sort_by = new_sort
        return nq

    @property
    def webui_link(self):
        return "{0:s}/#/search?{1}".format(self._cb.url, urllib.parse.urlencode(
            convert_query_params(self._get_query_parameters())))

    def and_(self, new_query):
        """Add a filter to this query. Equivalent to calling :py:meth:`where` on this object.

        :param str new_query: Query string - see the
            `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        return self.where(new_query)

    def where(self, new_query):
        """Add a filter to this query.

        :param str new_query: Query string - see the
            `Query Reference <http://developer.carbonblack.com/resources/query_overview.pdf>`_.
        :return: Query object
        :rtype: :py:class:`Query`
        """
        if self._raw_query:
            raise ApiError("Cannot call .where() on a raw query")

        nq = self._clone()
        if nq._query and len(nq._query) > 0:
            nq._query = "{0:s} {1:s}".format(self._query, new_query)
        else:
            nq._query = new_query

        return nq

    def facets(self, *args):
        """Retrieve a dictionary with the facets for this query.

        :param args: Any number of fields to use as facets
        :return: Facet data
        :rtype: dict
        """
        # TODO: make this interface better
        qargs = self._default_args.copy()
        qargs['facet'] = 'true'
        qargs['start'] = 0
        qargs['rows'] = 0
        qargs['facet.field'] = list(args)

        if self._query:
            qargs['q'] = self._query

        query_params = convert_query_params(qargs)
        return self._cb.get_object(self._doc_class.urlobject, query_parameters=query_params).get('facets', {})

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
        if self._count_valid:
            return self._total_results

        args = self._get_query_parameters()
        args['start'] = 0
        args['rows'] = 0

        qargs = convert_query_params(args)

        self._total_results = self._cb.get_object(self._doc_class.urlobject,
                                                  query_parameters=qargs).get('total_results', 0)

        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0):
        # iterate over total result set, 100 at a time

        args = self._get_query_parameters()
        args['start'] = start

        if self._sort_by:
            args['sort'] = self._sort_by

        if rows:
            args['rows'] = min(rows, self._batch_size)
        else:
            args['rows'] = self._batch_size

        still_querying = True
        current = start
        numrows = 0

        while still_querying:
            qargs = convert_query_params(args)
            result = self._cb.get_object(self._doc_class.urlobject, query_parameters=qargs)

            self._total_results = result.get('total_results')
            self._count_valid = True

            results = result.get('results', [])

            for item in results:
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['start'] = current

            if current >= self._total_results:
                break
            if not results:
                log.debug("server reported total_results overestimated the number of results for this query by {0}"
                          .format(self._total_results - current))
                log.debug("resetting total_results for this query to {0}".format(current))
                self._total_results = current
                break
