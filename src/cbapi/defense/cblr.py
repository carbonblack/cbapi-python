from cbapi.live_response_api import CbLRManagerBase, CbLRSessionBase, poll_status
from cbapi.errors import ObjectNotFoundError, TimeoutError
from cbapi.defense.models import Device


OS_LIVE_RESPONSE_ENUM = {
    "WINDOWS": 1,
    "LINUX": 2,
    "MAC": 4
}


class LiveResponseSession(CbLRSessionBase):
    def __init__(self, cblr_manager, session_id, sensor_id, session_data=None):
        super(LiveResponseSession, self).__init__(cblr_manager, session_id, sensor_id, session_data=session_data)
        device_info = self._cb.select(Device, self.sensor_id)
        self.os_type = OS_LIVE_RESPONSE_ENUM.get(device_info.deviceType, None)


class LiveResponseSessionManager(CbLRManagerBase):
    cblr_base = "/integrationServices/v3/cblr"
    cblr_session_cls = LiveResponseSession

    def _get_or_create_session(self, sensor_id):
        session_id = self._create_session(sensor_id)

        try:
            res = poll_status(self._cb, "{cblr_base}/session/{0}".format(session_id, cblr_base=self.cblr_base),
                              desired_status="ACTIVE", delay=1, timeout=360)
        except Exception:
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
            self._cb.put_object("{cblr_base}/session".format(session_id, cblr_base=self.cblr_base),
                                {"session_id": session_id, "status": "CLOSE"})
        except:
            pass

    def _create_session(self, sensor_id):
        response = self._cb.post_object("{cblr_base}/session/{0}".format(sensor_id, cblr_base=self.cblr_base),
                                        {"sensor_id": sensor_id}).json()
        session_id = response["id"]
        return session_id
