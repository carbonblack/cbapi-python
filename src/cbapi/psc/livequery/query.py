from cbapi.query import PaginatedQuery
from cbapi.errors import ApiError
import logging

log = logging.getLogger(__name__)


class Query(PaginatedQuery):
    def __init__(self, doc_class, cb):
        super(Query, self).__init__(doc_class, cb)
        self._query_token = None
        self._query_body = {"device_filter": {}}
        self._device_filter = self._query_body["device_filter"]

    def device_ids(self, device_ids):
        if not all(isinstance(device_id, int) for device_id in device_ids):
            raise ApiError("One or more invalid device IDs")
        self._device_filter["device_ids"] = device_ids
        return self

    def device_types(self, device_types):
        if not all(isinstance(device_type, str) for device_type in device_types):
            raise ApiError("One or more invalid device types")
        self._device_filter["device_types"] = device_types
        return self

    def policy_ids(self, policy_ids):
        if not all(isinstance(policy_id, int) for policy_id in policy_ids):
            raise ApiError("One or more invalid policy IDs")
        self._device_filter["policy_ids"] = policy_ids
        return self

    def _submit(self):
        if self._query_token is not None:
            raise ApiError("Query already submitted: token {0}".format(self._query_token))

