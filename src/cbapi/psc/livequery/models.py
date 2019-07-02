from __future__ import absolute_import
from cbapi.models import UnrefreshableModel, NewBaseModel
from .query import RunQuery, ResultQuery
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
        url = self.urlobject.format(self._cb.credentials.org_key, self.id)
        resp = self._cb.get_object(url)
        self._info = resp
        self._last_refresh_time = time.time()
        return True


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
        self._device = Result.Device(cb, initial_data=initial_data["device"])
        self._fields = Result.Fields(cb, initial_data=initial_data["fields"])
        self._metrics = Result.Metrics(cb, initial_data=initial_data["metrics"])

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
