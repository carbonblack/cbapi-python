from __future__ import absolute_import
from cbapi.errors import ApiError, InvalidObjectError
from cbapi.models import NewBaseModel, UnrefreshableModelMixin
import logging

log = logging.getLogger(__name__)


class Result(UnrefreshableModelMixin):
    primary_key = "id"
    swagger_meta_file = "psc/livequery/models/result.yaml"
