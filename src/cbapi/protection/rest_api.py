from ..utils import convert_query_params
from ..query import PaginatedQuery
from ..errors import UnauthorizedError, ApiError
from distutils.version import LooseVersion


from cbapi.connection import BaseAPI
import logging

log = logging.getLogger(__name__)


class CbProtectionAPI(BaseAPI):
    """The main entry point into the Carbon Black App Control API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi import CbProtectionAPI
    >>> cb = CbProtectionAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbProtectionAPI, self).__init__(product_name="protection", *args, **kwargs)

        self._server_info = None
        try:
            self._populate_server_info()
        except UnauthorizedError:
            raise UnauthorizedError(uri=self.url, message="Invalid API token for server {0:s}.".format(self.url))

        log.debug('Connected to Cb server version %s at %s'
                  % (self._server_info['ParityServerVersion'], self.session.server))
        self.cb_server_version = LooseVersion(self._server_info['ParityServerVersion'])

    def _perform_query(self, cls, **kwargs):
        if hasattr(cls, "_query_implementation"):
            return cls._query_implementation(self)
        else:
            return Query(cls, self, **kwargs)

    def _populate_server_info(self):
        self._server_info = dict((sc['name'], sc['value'])
                                 for sc in self.get_object("/api/bit9platform/v1/serverConfig"))

    @property
    def info(self):
        return self._server_info

    def select(self, cls, unique_id=None, *args, **kwargs):
        """Prepares a query against the Carbon Black data store.

        :param class cls: The Model class (for example, Computer, Process, Binary, FileInstance) to query
        :param unique_id: (optional) The unique id of the object to retrieve, to retrieve a single object by ID

        :returns: An instance of the Model class if a unique_id is provided, otherwise a Query object
        """

        try:
            min_server_version = cls._minimum_server_version()
            if self.cb_server_version < min_server_version:
                raise ApiError(
                    "{0} API requires at least server version {1}".format(cls.__name__, min_server_version))
        except AttributeError:
            pass

        return super(CbProtectionAPI, self).select(cls, unique_id=unique_id, *args, **kwargs)


class CbEnterpriseProtectionAPI(CbProtectionAPI):
    """
    Backwards compatibility for previous scripts
    """
    pass


class Query(PaginatedQuery):
    """Represents a prepared query to the Carbon Black App Control server.

    This object is returned as part of a :py:meth:`CbProtectionAPI.select`
    operation on models requested from the Carbon Black
    App Control server. You should not have to create this class yourself.

    The query is not executed on the server until it's accessed, either as an iterator (where it will generate values
    on demand as they're requested) or as a list (where it will retrieve the entire result set and save to a list).
    You can also call the Python built-in ``len()`` on this object to retrieve the total number of items matching
    the query.

    The syntax for query :py:meth:where and :py:meth:sort methods can be found in the
    `App Control REST API reference`_ posted on the Carbon Black Developer Network website.

    Examples::

    >>> from cbapi.protection import CbProtectionAPI, Computer
    >>> cb = CbProtectionAPI()
    >>> query = cb.select(Computer)                     # returns a Query object matching all Computers
    >>> query = query.where("ipAddress:10.201.2.*")     # add a filter to this Query
    >>> query = query.sort("processorSpeed DESC")       # sort by computer processor speed, descending
    >>> for comp in query:                              # uses the iterator to retrieve all results
    >>>     print(comp.name)
    >>> comps = query[:10]                              # retrieve the first ten results
    >>> len(query)                                      # retrieve the total count

    Notes:
        - The slicing operator only supports start and end parameters, but not step. ``[1:-1]`` is legal, but
          ``[1:2:-1]`` is not.
        - You can chain where clauses together to create AND queries; only objects that match all ``where`` clauses
          will be returned.

    .. _App Control REST API reference:
        https://developer.carbonblack.com/reference/enterprise-protection/8.0/rest-api/
    """
    def __init__(self, doc_class, cb, query=None):
        super(Query, self).__init__(doc_class, cb, None)

        if query:
            self._query = [query]
        else:
            self._query = []

        self._sort_by = None
        self._group_by = None
        self._batch_size = 1000

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        nq._query = self._query[::]
        nq._sort_by = self._sort_by
        nq._group_by = self._group_by
        nq._batch_size = self._batch_size
        return nq

    def where(self, q):
        """Add a filter to this query.

        :param str q: Query string - see the `App Control REST API reference`_.
        :return: Query object
        :rtype: :py:class:`Query`

        .. _App Control REST API reference:
            https://developer.carbonblack.com/reference/enterprise-protection/8.0/rest-api/
        """
        nq = self._clone()
        nq._query.append(q)
        return nq

    def and_(self, q):
        """Add a filter to this query. Equivalent to calling :py:meth:`where` on this object.

        :param str q: Query string - see the `App Control REST API reference`_.
        :return: Query object
        :rtype: :py:class:`Query`

        .. _App Control REST API reference:
            https://developer.carbonblack.com/reference/enterprise-protection/8.0/rest-api/
        """
        return self.where(q)

    def sort(self, new_sort):
        """Set the sort order for this query.

        :param str new_sort: Sort order - see the `App Control REST API reference`_.
        :return: Query object
        :rtype: :py:class:`Query`

        .. _App Control REST API reference:
            https://developer.carbonblack.com/reference/enterprise-protection/8.0/rest-api/
        """
        new_sort = new_sort.strip()
        nq = self._clone()
        if len(new_sort) == 0:
            nq._sort_by = None
        else:
            nq._sort_by = new_sort
        return nq

    def _count(self):
        args = {'limit': -1}
        if self._query:
            args['q'] = self._query

        query_args = convert_query_params(args)
        self._total_results = int(self._cb.get_object(self._doc_class.urlobject,
                                                      query_parameters=query_args).get("count", 0))
        self._count_valid = True
        return self._total_results

    def _search(self, start=0, rows=0):
        # iterate over total result set, 1000 at a time
        args = {}
        args['offset'] = start
        if self._sort_by:
            args['sort'] = self._sort_by
        if rows:
            args['limit'] = start + rows
        else:
            args['limit'] = start + self._batch_size

        current = start
        numrows = 0

        if self._query:
            args['q'] = self._query

        still_querying = True

        while still_querying:
            query_args = convert_query_params(args)
            result = self._cb.get_object(self._doc_class.urlobject, query_parameters=query_args)

            if len(result) == 0:
                break

            for item in result:
                yield item
                current += 1
                numrows += 1
                if rows and numrows == rows:
                    still_querying = False
                    break

            args['offset'] = current + 1

            if len(result) < self._batch_size:
                break
