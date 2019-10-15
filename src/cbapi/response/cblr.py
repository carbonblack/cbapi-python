from cbapi.live_response_api import CbLRManagerBase, CbLRSessionBase, poll_status
from cbapi.errors import ObjectNotFoundError, TimeoutError
from cbapi.response.models import Sensor


class LiveResponseSession(CbLRSessionBase):
    def __init__(self, cblr_manager, session_id, sensor_id, session_data=None):
        super(LiveResponseSession, self).__init__(cblr_manager, session_id, sensor_id, session_data=session_data)
        self.os_type = self._cb.select(Sensor, self.sensor_id).os_type


class LiveResponseSessionManager(CbLRManagerBase):
    cblr_base = "/api/v1/cblr"
    cblr_session_cls = LiveResponseSession

    def _get_or_create_session(self, sensor_id):
        sensor_sessions = [s for s in self._cb.get_object("{cblr_base}/session?active_only=true"
                                                          .format(cblr_base=self.cblr_base))
                           if s["sensor_id"] == sensor_id and s["status"] in ("pending", "active")]

        if len(sensor_sessions) > 0:
            session_id = sensor_sessions[0]["id"]
        else:
            session_id = self._create_session(sensor_id)

        try:
            res = poll_status(self._cb, "{cblr_base}/session/{0}".format(session_id, cblr_base=self.cblr_base),
                              desired_status="active", delay=1, timeout=360)
        except (ObjectNotFoundError, TimeoutError):
            # "close" the session, otherwise it will stay in a pending state
            self._close_session(session_id)

            # the Cb server will return a 404 if we don't establish a session in time, so convert this to a "timeout"
            raise TimeoutError(uri="{cblr_base}/session/{0}".format(session_id, cblr_base=self.cblr_base),
                               message="Could not establish session with sensor {0}".format(sensor_id),
                               error_code=404)
        else:
            return session_id, res

    def _close_session(self, session_id):
        try:
            session_data = self._cb.get_object("{cblr_base}/session/{0}".format(session_id, cblr_base=self.cblr_base))
            session_data["status"] = "close"
            self._cb.put_object("{cblr_base}/session/{0}".format(session_id, cblr_base=self.cblr_base), session_data)
        except Exception:
            pass

    def _create_session(self, sensor_id):
        response = self._cb.post_object("{cblr_base}/session".format(cblr_base=self.cblr_base),
                                        {"sensor_id": sensor_id}).json()
        session_id = response["id"]
        return session_id
