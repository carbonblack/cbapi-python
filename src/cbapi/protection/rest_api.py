from six import iteritems
from ..utils import convert_query_params
from ..query import PaginatedQuery

from cbapi.connection import BaseAPI
import logging

log = logging.getLogger(__name__)


class CbEnterpriseProtectionAPI(BaseAPI):
    def __init__(self, *args, **kwargs):
        super(CbEnterpriseProtectionAPI, self).__init__(product_name="protection", *args, **kwargs)

    def _perform_query(self, cls, query_string=None):
        return Query(cls, self, query_string)


class Query(PaginatedQuery):
    def __init__(self, doc_class, cb, query=None):
        super(Query, self).__init__(doc_class, cb, None)
        if query:
            self.query = [query]
        else:
            self.query = []

        self.sort_by = None
        self.group_by = None

    def where(self, q):
        self.query.append(q)
        return self

    def and_(self, q):
        return self.where(q)

    def sort(self, new_sort):
        new_sort = new_sort.strip()
        if len(new_sort) == 0:
            self.sort_by = None
        else:
            self.sort_by = new_sort
        return self

    def _count(self):
        args = {'limit': -1}
        if self.query:
            args['q'] = self.query

        query_args = convert_query_params(args)
        self.total_results = int(self.cb.get_object(self.doc_class.urlobject, query_parameters=query_args).get("count", 0))
        self.count_valid = True
        return self.total_results

    def _search(self, start=0, rows=0, perpage=1000):
        # iterate over total result set, 1000 at a time
        args = {}
        args['offset'] = start
        if self.sort_by:
            args['sort'] = self.sort_by
        if rows:
            args['limit'] = start + rows
        else:
            args['limit'] = start + perpage

        current = start
        numrows = 0

        if self.query:
            args['q'] = self.query

        still_querying = True

        while still_querying:
            query_args = convert_query_params(args)
            result = self.cb.get_object(self.doc_class.urlobject, query_parameters=query_args)

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

            if len(result) < perpage:
                break
