# NOTE: this is highly experimental and in no way reflects how the API will ultimately be designed

from __future__ import absolute_import

import random
import string
import threading
import time
import logging
from collections import defaultdict

from cbapi.errors import TimeoutError, ObjectNotFoundError
from six import itervalues
from concurrent.futures import ThreadPoolExecutor, as_completed
from cbapi import winerror


log = logging.getLogger(__name__)


class LiveResponseError(Exception):
    def __init__(self, message, details):
        message_list = [message]
        self.details = details
        # Details object:
        # {u'status': u'error', u'username': u'admin', u'sensor_id': 9, u'name': u'kill', u'completion': 1464319733.190924,
        # u'object': 1660, u'session_id': 7, u'result_type': u'WinHresult', u'create_time': 1464319733.171967,
        # u'result_desc': u'', u'id': 22, u'result_code': 2147942487}

        if self.details.get("status") == "error" and self.details.get("result_type") == "WinHresult":
            # attempt to decode the win32 error
            win32_error_text = "Unknown Win32 error code"
            try:
                hresult = int(self.details.get("result_code"))
                win32_error_text = "Win32 error code 0x%08X" % (hresult, )
                error_info = winerror.decode_hresult(hresult)
                if error_info:
                    win32_error_text += " ({0})".format(error_info)
            except:
                pass
            finally:
                message_list.append(win32_error_text)
        
        self.message = ": ".join(message_list)

    def __str__(self):
        return self.message


class LiveResponseSession(object):
    def __init__(self, scheduler, session_id, sensor_id):
        self.session_id = session_id
        self.sensor_id = sensor_id
        self.lr_scheduler = scheduler
        self.cb = scheduler._cb
        # TODO: refcount should be in a different object in the scheduler
        self.refcount = 1

    def get_file(self, file_name):
        data = {"name": "get file", "object": file_name}

        resp = self._lr_post_command(data).json()
        file_id = resp.get('file_id', None)
        command_id = resp.get('id', None)

        self._poll_command(command_id)
        file_content = self.cb.session.get("/api/v1/cblr/session/{0}/file/{1}/content".format(self.session_id,
                                                                                                 file_id)).content

        return file_content

    def kill_process(self, pid):
        data = {"name": "kill", "object": pid}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        try:
            self._poll_command(command_id, timeout=10, delay=0.1)
        except TimeoutError:
            return False

        return True

    def create_process(self, command_string, wait_for_output=True, wait_timeout=30):
        # process is:
        # - create a temporary file name
        # - create the process, writing output to a temporary file
        # - wait for the process to complete
        # - get the temporary file from the endpoint
        # - delete the temporary file

        data = {"name": "create process", "object": command_string, "wait": False}

        if wait_for_output:
            randfile = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(12)])
            workdir = 'c:\\windows\\carbonblack'       # TODO: cross-platform
            randfilename = '%s\\cblr.%s.tmp' % (workdir, randfile)
            data["working_directory"] = workdir
            data["output_file"] = randfilename

        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        if wait_for_output:
            self._poll_command(command_id, timeout=wait_timeout)

            # now the file is ready to be read

            file_content = self.get_file(randfilename)
            # delete the file
            self._lr_post_command({"name": "delete file", "object": randfilename})

            return file_content

    def get_processes(self):
        data = {"name": "process list"}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        return self._poll_command(command_id).get("processes")

    def _poll_command(self, command_id, **kwargs):
        return poll_status(self.cb, "/api/v1/cblr/session/{0}/command/{1}".format(self.session_id, command_id),
                           **kwargs)

    def _lr_post_command(self, data):
        retries = 5

        while retries:
            try:
                data["session_id"] = self.session_id
                resp = self.cb.post_object("/api/v1/cblr/session/{0}/command".format(self.session_id), data)
            except ObjectNotFoundError:
                self.session_id = self.lr_scheduler.request_session(self.session_id, force_new_session=True)
                retries -= 1
                continue
            else:
                return resp


def jobrunner(callable, cb, sensor_id):
    with cb.select(Sensor, sensor_id).lr_session() as sess:
        return callable(sess)


class LiveResponseScheduler(object):
    def __init__(self, cb, timeout=30, max_workers=10):
        self._timeout = timeout
        self._cb = cb
        self._sessions = {}
        self._session_lock = threading.RLock()

        self._cleanup_thread = threading.Thread(target=self._session_keepalive_thread)
        self._cleanup_thread.daemon = True
        self._cleanup_thread.start()

        self._job_workers = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs = defaultdict(list)

    def submit_job(self, tag, job, sensor_list):
        for s in sensor_list:
            self._jobs[tag].append(self._job_workers.submit(jobrunner, job, self._cb, s))

    def job_results(self, tag):
        return as_completed(self._jobs[tag])

    def _session_keepalive_thread(self):
        log.debug("Starting Live Response scheduler cleanup task")
        while True:
            time.sleep(self._timeout)

            delete_list = []
            with self._session_lock:
                for sensor in itervalues(self._sessions):
                    if sensor.refcount == 0:
                        delete_list.append(sensor.sensor_id)
                    else:
                        self._send_keepalive(sensor.session_id)

                for sensor_id in delete_list:
                    del self._sessions[sensor_id]

    def request_session(self, sensor_id, force_new_session=False):
        with self._session_lock:
            if sensor_id in self._sessions and not force_new_session:
                session = self._sessions[sensor_id]
                self._sessions[sensor_id].refcount += 1
            else:
                session = self._get_or_create_session(sensor_id)
                self._sessions[sensor_id] = session

        return session

    def close_session(self, sensor_id):
        with self._session_lock:
            self._sessions[sensor_id].refcount -= 1

    def _send_keepalive(self, session_id):
        log.debug("Sending keepalive message for session id {0}".format(session_id))
        self._cb.get_object("/api/v1/cblr/session/{0}/keepalive".format(session_id))

    def _get_or_create_session(self, sensor_id):
        sensor_sessions = [s for s in self._cb.get_object("/api/v1/cblr/session")
                           if s["sensor_id"] == sensor_id and s["status"] in ("pending", "active")]

        if len(sensor_sessions) > 0:
            session = LiveResponseSession(self, sensor_sessions[0]["id"], sensor_id)
        else:
            session = self._create_session(sensor_id)

        poll_status(self._cb, "/api/v1/cblr/session/{0}".format(session.session_id), desired_status="active")
        return session

    def _create_session(self, sensor_id):
        response = self._cb.post_object("/api/v1/cblr/session", {"sensor_id": sensor_id}).json()
        session_id = response["id"]
        return LiveResponseSession(self, session_id, sensor_id)


class GetFileJob(object):
    def __init__(self, file_name):
        self._file_name = file_name

    def run(self, session):
        return session.get_file(self._file_name)


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


if __name__ == "__main__":
    from cbapi.response import CbEnterpriseResponseAPI
    from cbapi.response.models import Sensor
    import logging
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())

    logging.getLogger("cbapi").setLevel(logging.DEBUG)

    c = CbEnterpriseResponseAPI()
    j = GetFileJob(r"c:\test.txt")
    with c.select(Sensor, 9).lr_session() as lr_session:
        file_contents = lr_session.get_file(r"c:\test.txt")

    c._lr_scheduler.submit_job("test", j.run, [9,])
    for x in c._lr_scheduler.job_results("test"):
        print(x.result())

