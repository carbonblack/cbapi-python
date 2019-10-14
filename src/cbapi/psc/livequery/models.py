from __future__ import absolute_import
from cbapi.models import UnrefreshableModel, NewBaseModel
from cbapi.errors import ApiError, ServerError
from .query import RunQuery, RunHistoryQuery,  ResultQuery, FacetQuery
import logging
import time

log = logging.getLogger(__name__)


class Run(NewBaseModel):
    """
    Represents a LiveQuery run.

    Example::

    >>> run = cb.select(Run, run_id)
    >>> print(run.name, run.sql, run.create_time)
    >>> print(run.status, run.match_count)
    >>> run.refresh()
    """
    primary_key = "id"
    swagger_meta_file = "psc/livequery/models/run.yaml"
    urlobject = "/livequery/v1/orgs/{}/runs"
    urlobject_single = "/livequery/v1/orgs/{}/runs/{}"
    _is_deleted = False

    def __init__(self, cb, model_unique_id=None, initial_data=None):
        if initial_data is not None:
            item = initial_data
        elif model_unique_id is not None:
            url = self.urlobject_single.format(cb.credentials.org_key, model_unique_id)
            item = cb.get_object(url)

        model_unique_id = item.get("id")

        super(Run, self).__init__(
            cb,
            model_unique_id=model_unique_id,
            initial_data=item,
            force_init=False,
            full_doc=True,
        )

    @classmethod
    def _query_implementation(cls, cb):
        return RunQuery(cls, cb)

    def _refresh(self):
        if self._is_deleted:
            raise ApiError("cannot refresh a deleted query")
        url = self.urlobject_single.format(self._cb.credentials.org_key, self.id)
        resp = self._cb.get_object(url)
        self._info = resp
        self._last_refresh_time = time.time()
        return True

    def stop(self):
        if self._is_deleted:
            raise ApiError("cannot stop a deleted query")
        url = self.urlobject_single.format(self._cb.credentials.org_key, self.id) + "/status"
        result = self._cb.put_object(url, {'status': 'CANCELLED'})
        if (result.status_code == 200):
            try:
                self._info = result.json()
                self._last_refresh_time = time.time()
                return True
            except Exception:
                raise ServerError(result.status_code, "Cannot parse response as JSON: {0:s}".format(result.content))
        return False

    def delete(self):
        if self._is_deleted:
            return True  # already deleted
        url = self.urlobject_single.format(self._cb.credentials.org_key, self.id)
        result = self._cb.delete_object(url)
        if result.status_code == 200:
            self._is_deleted = True
            return True
        return False


class RunHistory(Run):
    """
    Represents a historical LiveQuery ``Run``.
    """
    urlobject_history = "/livequery/v1/orgs/{}/runs/_search"

    def __init__(self, cb, initial_data=None):
        item = initial_data
        model_unique_id = item.get("id")
        super(Run, self).__init__(cb,
                                  model_unique_id, initial_data=item,
                                  force_init=False, full_doc=True)

    @classmethod
    def _query_implementation(cls, cb):
        return RunHistoryQuery(cls, cb)


class Result(UnrefreshableModel):
    """
    Represents a single result from a LiveQuery ``Run``.
    """
    primary_key = "id"
    swagger_meta_file = "psc/livequery/models/result.yaml"
    urlobject = "/livequery/v1/orgs/{}/runs/{}/results/_search"

    class Device(UnrefreshableModel):
        """
        Represents device information for a result.
        """
        primary_key = "id"

        def __init__(self, cb, initial_data):
            super(Result.Device, self).__init__(
                cb,
                model_unique_id=initial_data["id"],
                initial_data=initial_data,
                force_init=False,
                full_doc=True,
            )

    class Fields(UnrefreshableModel):
        """
        Represents the fields of a result.
        """
        def __init__(self, cb, initial_data):
            super(Result.Fields, self).__init__(
                cb,
                model_unique_id=None,
                initial_data=initial_data,
                force_init=False,
                full_doc=True,
            )

    class Metrics(UnrefreshableModel):
        """
        Represents the metrics for a result.
        """
        def __init__(self, cb, initial_data):
            super(Result.Metrics, self).__init__(
                cb,
                model_unique_id=None,
                initial_data=initial_data,
                force_init=False,
                full_doc=True,
            )

    @classmethod
    def _query_implementation(cls, cb):
        return ResultQuery(cls, cb)

    def __init__(self, cb, initial_data):
        super(Result, self).__init__(
            cb,
            model_unique_id=initial_data["id"],
            initial_data=initial_data,
            force_init=False,
            full_doc=True,
        )
        self._run_id = initial_data["id"]
        self._device = Result.Device(cb, initial_data=initial_data["device"])
        self._fields = Result.Fields(cb, initial_data=initial_data["fields"])
        if "metrics" in initial_data:
            self._metrics = Result.Metrics(cb, initial_data=initial_data["metrics"])
        else:
            self._metrics = Result.Metrics(cb, initial_data=None)

    @property
    def device_(self):
        """
        Returns the reified ``Result.Device`` for this result.
        """
        return self._device

    @property
    def fields_(self):
        """
        Returns the reified ``Result.Fields`` for this result.
        """
        return self._fields

    @property
    def metrics_(self):
        """
        Returns the reified ``Result.Metrics`` for this result.
        """
        return self._metrics

    def query_device_summaries(self):
        return self._cb.select(DeviceSummary).run_id(self._run_id)

    def query_result_facets(self):
        return self._cb.select(ResultFacet).run_id(self._run_id)

    def query_device_summary_facets(self):
        return self._cb.select(DeviceSummaryFacet).run_id(self._run_id)


class DeviceSummary(UnrefreshableModel):
    """
    Represents the summary of results from a single device during a single LiveQuery ``Run``.
    """
    primary_key = "id"
    swagger_meta_file = "psc/livequery/models/device_summary.yaml"
    urlobject = "/livequery/v1/orgs/{}/runs/{}/results/device_summaries/_search"

    class Metrics(UnrefreshableModel):
        """
        Represents the metrics for a result.
        """
        def __init__(self, cb, initial_data):
            super(DeviceSummary.Metrics, self).__init__(
                cb,
                model_unique_id=None,
                initial_data=initial_data,
                force_init=False,
                full_doc=True,
            )

    @classmethod
    def _query_implementation(cls, cb):
        return ResultQuery(cls, cb)

    def __init__(self, cb, initial_data):
        super(DeviceSummary, self).__init__(
            cb,
            model_unique_id=initial_data["id"],
            initial_data=initial_data,
            force_init=False,
            full_doc=True,
        )
        self._metrics = DeviceSummary.Metrics(cb, initial_data=initial_data["metrics"])

    @property
    def metrics_(self):
        """
        Returns the reified ``DeviceSummary.Metrics`` for this result.
        """
        return self._metrics


class ResultFacet(UnrefreshableModel):
    """
    Represents the summary of results for a single field in a LiveQuery ``Run``.
    """
    primary_key = "field"
    swagger_meta_file = "psc/livequery/models/facet.yaml"
    urlobject = "/livequery/v1/orgs/{}/runs/{}/results/_facet"

    class Values(UnrefreshableModel):
        """
        Represents the values associated with a field.
        """
        def __init__(self, cb, initial_data):
            super(ResultFacet.Values, self).__init__(
                cb,
                model_unique_id=None,
                initial_data=initial_data,
                force_init=False,
                full_doc=True,
            )

    @classmethod
    def _query_implementation(cls, cb):
        return FacetQuery(cls, cb)

    def __init__(self, cb, initial_data):
        super(ResultFacet, self).__init__(
            cb,
            model_unique_id=None,
            initial_data=initial_data,
            force_init=False,
            full_doc=True
        )
        self._values = ResultFacet.Values(cb, initial_data=initial_data["values"])

    @property
    def values_(self):
        """
        Returns the reified ``ResultFacet.Values`` for this result.
        """
        return self._values


class DeviceSummaryFacet(ResultFacet):
    """
    Represents the summary of results for a single device summary in a LiveQuery ``Run``.
    """
    urlobject = "/livequery/v1/orgs/{}/runs/{}/results/device_summaries/_facet"

    def __init__(self, cb, initial_data):
        super(DeviceSummaryFacet, self).__init__(cb, initial_data)
