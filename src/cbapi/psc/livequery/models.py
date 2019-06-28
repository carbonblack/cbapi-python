from __future__ import absolute_import
from cbapi.errors import ApiError
from cbapi.models import UnrefreshableModel, NewBaseModel
import logging
import time

log = logging.getLogger(__name__)


class Run(NewBaseModel):
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

    def _refresh(self):
        url = self.urlobject.format(self._cb.credentials.org_key, self.id)
        resp = self._cb.get_object(url)
        self._info = resp
        self._last_refresh_time = time.time()
        return True


class Result(UnrefreshableModel):
    primary_key = "id"
    swagger_meta_file = "psc/livequery/models/result.yaml"
