# NOTE: this is highly experimental and in no way reflects how the API will ultimately be designed

from __future__ import absolute_import
import threading
import time
import contextlib
import logging
from cbapi.errors import TimeoutError
from six import itervalues


log = logging.getLogger(__name__)


class LiveResponseError(Exception):
    def __init__(self, message, details):
        self.message = message
        self.details = details


def poll_status(cb, url, desired_status="complete", timeout=120, delay=0.5):
    start_time = time.time()
    status = None

    while status != desired_status and time.time() - start_time < timeout:
        res = cb.get_object(url)
        if res["status"] == desired_status:
            return res
        elif res["status"] == "error":
            raise LiveResponseError("error returned from Live Response", details=res)
        else:
            time.sleep(delay)

    raise TimeoutError(url, message="timeout polling for Live Response")


# TODO: should this class be "smarter" and handle all the HTTP comms? Perhaps this can handle transparent
# reconnection in case the session times out, the server restarts, etc... in that case, do we need the "scheduler"?
class LiveResponseSession(object):
    def __init__(self, cb, session_id, sensor_id):
        self.session_id = session_id
        self.sensor_id = sensor_id
        self.cb = cb
        self.refcount = 1


class LiveResponseScheduler(threading.Thread):
    def __init__(self, cb, timeout=30):
        super(LiveResponseScheduler, self).__init__()
        self._timeout = timeout
        self._cb = cb
        self._sessions = {}
        self._session_lock = threading.RLock()

        self.daemon = True

    def run(self):
        while True:
            delete_list = []
            with self._session_lock:
                for sensor in itervalues(self._sessions):
                    if sensor.refcount == 0:
                        delete_list.append(sensor.sensor_id)
                    else:
                        self._send_keepalive(sensor.session_id)

                for sensor_id in delete_list:
                    del self._sessions[sensor_id]

            time.sleep(self._timeout)

    @contextlib.contextmanager
    def session(self, sensor):
        with self._session_lock:
            if sensor.id in self._sessions:
                session = self._sessions[sensor.id]
                self._sessions[sensor.id].refcount += 1
            else:
                session = self._get_or_create_session(sensor.id)
                self._sessions[sensor.id] = session

        yield session

        with self._session_lock:
            self._sessions[sensor.id].refcount -= 1

    def _send_keepalive(self, sensor_id):
        log.debug("Sending keepalive message for sensor id {0}".format(sensor_id))
        self._cb.get_object("/api/v1/cblr/session/{0}/keepalive".format(sensor_id))

    def _get_or_create_session(self, sensor_id):
        sensor_sessions = [s for s in self._cb.get_object("/api/v1/cblr/session")
                           if s["sensor_id"] == sensor_id and s["status"] in ("pending", "active")]

        if len(sensor_sessions) > 0:
            session = LiveResponseSession(self._cb, sensor_sessions[0]["id"], sensor_id)
        else:
            session = self._create_session(sensor_id)

        poll_status(self._cb, "/api/v1/cblr/session/{0}".format(session.session_id), desired_status="active")
        return session

    def _create_session(self, sensor_id):
        response = self._cb.post_object("/api/v1/cblr/session", {"sensor_id": sensor_id}).json()
        session_id = response["id"]
        return LiveResponseSession(self._cb, session_id, sensor_id)


class LiveResponseJob(object):
    def run(self, scheduler, sensor):
        with scheduler.session(sensor) as lr_session:
            self.run_job(lr_session)

    def run_job(self, session):
        pass


class GetFileJob(LiveResponseJob):
    def __init__(self, file_name):
        super(GetFileJob, self).__init__()
        self._file_name = file_name
        self._file_contents = None

    def run_job(self, session):
        data = {"session_id": session.session_id, "name": "get file", "object": self._file_name}

        resp = session.cb.post_object("/api/v1/cblr/session/{0}/command".format(session.session_id), data).json()
        file_id = resp.get('file_id', None)
        command_id = resp.get('id', None)

        poll_status(session.cb, "/api/v1/cblr/session/{0}/command/{1}".format(session.session_id, command_id))
        file_content = session.cb.session.get("/api/v1/cblr/session/{0}/file/{1}/content".format(session.session_id,
                                                                                                 file_id)).content
        self._file_contents = file_content

        print file_content
        return True

    def get_result(self):
        return self._file_contents


if __name__ == "__main__":
    from cbapi.response import CbEnterpriseResponseAPI
    from cbapi.response.models import Sensor
    import logging
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())

    logging.getLogger("cbapi").setLevel(logging.DEBUG)

    c = CbEnterpriseResponseAPI()
    s = LiveResponseScheduler(c)
    s.start()
    GetFileJob(r"c:\test.txt").run(s, c.select(Sensor, 9))
