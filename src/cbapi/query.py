#!/usr/bin/env python

from __future__ import absolute_import
from .errors import ApiError, MoreThanOneResultError
from six import iteritems
from six.moves import range
import logging
log = logging.getLogger(__name__)


class BaseQuery(object):
    def __init__(self, query=None):
        self.query = query

    def all(self):
        return self._query()

    def first(self):
        res = self[:1]
        if not len(res):
            return None
        return res[0]

    def one(self):
        res = self[:2]
        if len(res) == 0:
            raise MoreThanOneResultError(message="0 results for query {0:s}".format(self.query))
        if len(res) > 1:
            raise MoreThanOneResultError(message="{0:d} results found for query {1:s}".format(len(self), self.query))
        return res[0]

    def _query(self):
        return None

    def __len__(self):
        return 0

    def __getitem__(self, item):
        return None

    def __iter__(self):
        return self._query()


class SimpleQuery(BaseQuery):
    def __init__(self, cls, cb, urlobject=None):
        super(SimpleQuery, self).__init__()

        self.doc_class = cls
        if not urlobject:
            self.urlobject = cls.urlobject
        else:
            self.urlobject = urlobject
        self.cb = cb
        self._full_init = False
        self._results = []
        self.query = {}

    def _match_query(self, i):
        for k, v in iteritems(self.query):
            target = getattr(i, k, None)
            if target is None:
                return False
            if str(target).lower() != v:
                return False
        return True

    @property
    def results(self):
        if not self._full_init:
            self._results = []
            for item in self.cb.get_object(self.urlobject):
                t = self.doc_class.new_object(self.cb, item)
                if self._match_query(t):
                    self._results.append(t)
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
        if self.query:
            raise ApiError("Cannot have multiple 'where' clauses")

        field, value = new_query.split(':')
        self.query[field] = value

        self._full_init = False
        return self

    def _query(self):
        for item in self.results:
            yield item


class PaginatedQuery(BaseQuery):
    def __init__(self, cls, cb, query=None):
        super(PaginatedQuery, self).__init__(query)
        self.doc_class = cls
        self.cb = cb
        # TODO: this should be subject to a TTL
        self.total_results = 0
        self.count_valid = False

    def __len__(self):
        if self.count_valid:
            return self.total_results
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
                return list(self._query(start, numrows))
            except StopIteration:
                return []
        elif isinstance(item, int):
            if item < 0:
                item += len(self)
            if item < 0:
                return None

            try:
                return next(self._query(item, 1))
            except StopIteration:
                return None
        else:
            raise TypeError("invalid type")

    def _query(self, start=0, numrows=0):
        for item in self._search(start=start, rows=numrows):
            yield self.doc_class.new_object(self.cb, item)

