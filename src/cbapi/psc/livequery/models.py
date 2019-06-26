from __future__ import absolute_import
from cbapi.errors import ApiError, InvalidObjectError
from cbapi.models import UnrefreshableModel, NewBaseModel
import logging
import time

log = logging.getLogger(__name__)


class Run(NewBaseModel):
    primary_key = "id"
    swagger_meta_file = "psc/livequery/models/run.yaml"
    urlobject = "/livequery/v1/orgs/{}/runs"

    def __init__(self, cb, initial_data):
        super(Run, self).__init__(
            cb,
            model_unique_id=initial_data["id"],
            initial_data=initial_data,
            force_init=False,
            full_doc=True,
        )

    def _refresh(self):
        url = "/livequery/v1/orgs/{}/runs/{}".format(
            self._cb.credentials.org_key,
            self.id
        )
        resp = self._cb.get_object(url)
        self._info = resp
        self._last_refresh_time = time.time()
        return True


class Result(UnrefreshableModel):
    primary_key = "id"
    swagger_meta_file = "psc/livequery/models/result.yaml"
