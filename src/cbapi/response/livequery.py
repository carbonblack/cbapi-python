#!/usr/bin/env python

"""CBAPI Live Query implementation"""

from cbapi.errors import ApiError


class LiveQuery:
    def __init__(self, cb):
        self._cb = cb
        self._request_body = {"query": ""}
        self._cached_results = None

    @classmethod
    def enable(cls, cb, flag=True):
        cb.put_object("/api/v1/config_mgmt/LiveQueryEnabled", {"LiveQueryEnabled": {"value": flag}})

    @classmethod
    def disable(cls, cb):
        LiveQuery.enable(cb, False)

    @classmethod
    def _query_implementation(cls, cb):
        return LiveQuery(cb)

    def where(self, **kwargs):
        param = kwargs.pop("sql", None)
        if param:
            self.set_query(param)
        param = kwargs.pop("group_ids", None)
        if param:
            self.set_group_ids(param)
        param = kwargs.pop("sensor_ids", None)
        if param:
            self.set_sensor_ids(param)
        return self

    def set_query(self, query):
        self._request_body["query"] = query
        self._cached_results = None
        return self

    def set_group_ids(self, ids):
        if isinstance(ids, list):
            if not all([isinstance(value, int) for value in ids]):
                raise ApiError("group IDs must all be integer")
            self._request_body["group_ids"] = ids
        elif isinstance(ids, int):
            self._request_body["group_ids"] = [ids]
        else:
            raise ApiError("group IDs must be either int or list of ints")
        self._cached_results = None
        return self

    def set_sensor_ids(self, ids):
        if isinstance(ids, list):
            if not all([isinstance(value, int) for value in ids]):
                raise ApiError("sensor IDs must all be integer")
            self._request_body["sensor_ids"] = ids
        elif isinstance(ids, int):
            self._request_body["sensor_ids"] = [ids]
        else:
            raise ApiError("sensor IDs must be either int or list of ints")
        self._cached_results = None
        return self

    def _execute(self):
        if not self._cached_results:
            self._cached_results = self._cb.post_object("/api/v1/livequery/query", body=self._request_body)
        return self._cached_results
