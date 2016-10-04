#!/usr/bin/env python

from __future__ import absolute_import
import copy
import six
from .errors import ApiError, MoreThanOneResultError
from six import iteritems
from six.moves import range
import logging


log = logging.getLogger(__name__)


class BaseQuery(object):
    def __init__(self, query=None):
        self._query = query

    def _clone(self):
        return self.__class__(self._query)

    def all(self):
        return self._perform_query()

    def first(self):
        res = self[:1]
        if not len(res):
            return None
        return res[0]

    def one(self):
        res = self[:2]
        if len(res) == 0:
            raise MoreThanOneResultError(message="0 results for query {0:s}".format(self._query))
        if len(res) > 1:
            raise MoreThanOneResultError(message="{0:d} results found for query {1:s}".format(len(self), self._query))
        return res[0]

    def _perform_query(self):
        # This has the effect of generating an empty iterator.
        # See http://stackoverflow.com/questions/13243766/python-empty-generator-function
        return
        yield

    def __len__(self):
        return 0

    def __getitem__(self, item):
        return None

    def __iter__(self):
        return self._perform_query()


class SimpleQuery(BaseQuery):
    def __init__(self, cls, cb, urlobject=None):
        super(SimpleQuery, self).__init__()

        self._doc_class = cls
        if not urlobject:
            self._urlobject = cls.urlobject
        else:
            self._urlobject = urlobject
        self._cb = cb
        self._full_init = False
        self._results = []
        self._query = {}
        self._sort_by = None

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb)
        nq._urlobject = self._urlobject
        nq._full_init = self._full_init
        nq._results = self._results[::]
        nq._query = copy.deepcopy(self._query)
        nq._sort_by = self._sort_by

        return nq

    def _match_query(self, i):
        for k, v in iteritems(self._query):
            if isinstance(v, six.string_types):
                v = v.lower()
            target = getattr(i, k, None)
            if target is None:
                return False
            if str(target).lower() != v:
                return False
        return True

    def _sort(self, result_set):
        if self._sort_by is not None:
            return sorted(result_set, key=lambda x: getattr(x, self._sort_by, 0), reverse=True)
        else:
            return result_set

    @property
    def results(self):
        if not self._full_init:
            self._results = []
            for item in self._cb.get_object(self._urlobject, default=[]):
                t = self._doc_class.new_object(self._cb, item, full_doc=True)
                if self._match_query(t):
                    self._results.append(t)
            self._results = self._sort(self._results)
            self._full_init = True

        return self._results

    def __len__(self):
        return len(self.results)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return [self.results[ii] for ii in range(*item.indices(len(self)))]
        elif isinstance(item, int):
            return self.results[item]
        else:
            raise TypeError("Invalid argument type")

    def where(self, new_query):
        if self._query:
            raise ApiError("Cannot have multiple 'where' clauses")

        nq = self._clone()
        field, value = new_query.split(':', 1)
        nq._query[field] = value
        nq._full_init = False
        return nq

    def _perform_query(self):
        for item in self.results:
            yield item

    def sort(self, new_sort):
        nq = self._clone()
        nq._sort_by = new_sort
        return nq


class PaginatedQuery(BaseQuery):
    def __init__(self, cls, cb, query=None):
        super(PaginatedQuery, self).__init__(query)
        self._doc_class = cls
        self._cb = cb
        # TODO: this should be subject to a TTL
        self._total_results = 0
        self._count_valid = False

    def _clone(self):
        nq = self.__class__(self._doc_class, self._cb, query=self._query)
        return nq

    def __len__(self):
        if self._count_valid:
            return self._total_results
        return self._count()

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.step and item.step != 1:
                raise ValueError("steps not supported")

            must_count_result_set = False
            if item.start is None or item.start == 0:
                start = 0
            else:
                start = item.start
                if item.start < 0:
                    must_count_result_set = True

            if item.stop is None or item.stop == 0:
                numrows = 0
            else:
                numrows = item.stop - start
                if item.stop < 0:
                    must_count_result_set = True
                elif numrows <= 0:
                    return []

            if must_count_result_set:
                log.debug('Must count result set')
                # general case
                item_range = range(*item.indices(len(self)))
                if not len(item_range):
                    return []

                start, numrows = item_range[0], len(item_range)

            try:
                return list(self._perform_query(start, numrows))
            except StopIteration:
                return []
        elif isinstance(item, int):
            if item < 0:
                item += len(self)
            if item < 0:
                return None

            try:
                return next(self._perform_query(item, 1))
            except StopIteration:
                return None
        else:
            raise TypeError("invalid type")

    def _perform_query(self, start=0, numrows=0):
        for item in self._search(start=start, rows=numrows):
            yield self._doc_class.new_object(self._cb, item)
