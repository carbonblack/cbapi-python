from __future__ import absolute_import

import random
import string
import threading
import time
import logging
from collections import defaultdict

import shutil

from cbapi.errors import TimeoutError, ObjectNotFoundError, ApiError, ServerError
from six import itervalues
from concurrent.futures import ThreadPoolExecutor, as_completed
from cbapi import winerror

from cbapi.response.models import Sensor


log = logging.getLogger(__name__)


class LiveResponseError(Exception):
    def __init__(self, details):
        message_list = []

        self.details = details
        self.win32_error = None
        self.decoded_win32_error = ""

        # Details object:
        # {u'status': u'error', u'username': u'admin', u'sensor_id': 9, u'name': u'kill', u'completion': 1464319733.190924,
        # u'object': 1660, u'session_id': 7, u'result_type': u'WinHresult', u'create_time': 1464319733.171967,
        # u'result_desc': u'', u'id': 22, u'result_code': 2147942487}

        if self.details.get("status") == "error" and self.details.get("result_type") == "WinHresult":
            # attempt to decode the win32 error
            win32_error_text = "Unknown Win32 error code"
            try:
                self.win32_error = int(self.details.get("result_code"))
                win32_error_text = "Win32 error code 0x%08X" % (self.win32_error,)
                self.decoded_win32_error = winerror.decode_hresult(self.win32_error)
                if self.decoded_win32_error:
                    win32_error_text += " ({0})".format(self.decoded_win32_error)
            except:
                pass
            finally:
                message_list.append(win32_error_text)
        
        self.message = ": ".join(message_list)

    def __str__(self):
        return self.message


class LiveResponseSession(object):
    MAX_RETRY_COUNT = 5

    def __init__(self, scheduler, session_id, sensor_id, session_data=None):
        self.session_id = session_id
        self.sensor_id = sensor_id
        self._lr_scheduler = scheduler
        self._cb = scheduler._cb
        # TODO: refcount should be in a different object in the scheduler
        self._refcount = 1
        self._closed = False

        self.session_data = session_data
        self.os_type = self._cb.select(Sensor, self.sensor_id).os_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._lr_scheduler.close_session(self.sensor_id)
        self._closed = True

    def get_session_archive(self):
        response = self._cb.session.get("/api/v1/cblr/session/{0}/archive".format(self.session_id), stream=True)
        response.raw.decode_content = True
        return response.raw

    #
    # File operations
    #
    def get_raw_file(self, file_name, timeout=None, delay=None):
        data = {"name": "get file", "object": file_name}

        resp = self._lr_post_command(data).json()
        file_id = resp.get('file_id', None)
        command_id = resp.get('id', None)

        self._poll_command(command_id, timeout=timeout, delay=delay)
        response = self._cb.session.get("/api/v1/cblr/session/{0}/file/{1}/content".format(self.session_id,
                                                                                           file_id), stream=True)
        response.raw.decode_content = True
        return response.raw

    def get_file(self, file_name):
        fp = self.get_raw_file(file_name)
        content = fp.read()
        fp.close()

        return content

    def delete_file(self, filename):
        data = {"name": "delete file", "object": filename}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        self._poll_command(command_id)

    def put_file(self, infp, remote_filename):
        data = {"name": "put file", "object": remote_filename}
        file_id = self._upload_file(infp)
        data["file_id"] = file_id

        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        self._poll_command(command_id)

    def list_directory(self, dir_name):
        data = {"name": "directory list", "object": dir_name}
        resp = self._lr_post_command(data).json()
        command_id = resp.get("id")
        return self._poll_command(command_id).get("files", [])

    def create_directory(self, dir_name):
        data = {"name": "create directory", "object": dir_name}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        self._poll_command(command_id)

    def path_join(self, *dirnames):
        if self.os_type == 1:
            # Windows
            return "\\".join(dirnames)
        else:
            # Unix/Mac OS X
            return "/".join(dirnames)

    def path_islink(self, fi):
        # TODO: implement
        return False

    def walk(self, top, topdown=True, onerror=None, followlinks=False):
        try:
            allfiles = self.list_directory(self.path_join(top, "*"))
        except Exception as err:
            if onerror is not None:
                onerror(err)
            return

        dirnames = []
        filenames = []

        for fn in allfiles:
            if "DIRECTORY" in fn["attributes"]:
                if fn["filename"] not in (".", ".."):
                    dirnames.append(fn)
            else:
                filenames.append(fn)

        if topdown:
            yield top, [fn["filename"] for fn in dirnames], [fn["filename"] for fn in filenames]

        for name in dirnames:
            new_path = self.path_join(top, name["filename"])
            if followlinks or not self.path_islink(new_path):
                for x in self.walk(new_path, topdown, onerror, followlinks):
                    yield x
        if not topdown:
            yield top, [fn["filename"] for fn in dirnames], [fn["filename"] for fn in filenames]


    #
    # Process operations
    #
    def kill_process(self, pid):
        data = {"name": "kill", "object": pid}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        try:
            self._poll_command(command_id, timeout=10, delay=0.1)
        except TimeoutError:
            return False

        return True

    def create_process(self, command_string, wait_for_output=True, remote_output_file_name=None,
                       working_directory=None, wait_timeout=30):
        # process is:
        # - create a temporary file name
        # - create the process, writing output to a temporary file
        # - wait for the process to complete
        # - get the temporary file from the endpoint
        # - delete the temporary file

        data = {"name": "create process", "object": command_string, "wait": False}

        if wait_for_output and not remote_output_file_name:
            randfilename = self._random_file_name()
            data["output_file"] = randfilename

        if working_directory:
            data["working_directory"] = working_directory

        if remote_output_file_name:
            data["output_file"] = remote_output_file_name

        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        if wait_for_output:
            self._poll_command(command_id, timeout=wait_timeout)

            # now the file is ready to be read

            file_content = self.get_file(data["output_file"])
            # delete the file
            self._lr_post_command({"name": "delete file", "object": data["output_file"]})

            return file_content

    def list_processes(self):
        data = {"name": "process list"}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        return self._poll_command(command_id).get("processes", [])

    #
    # Registry operations
    #
    # returns dictionary with 2 entries ("values" and "sub_keys")
    #  "values" is a list containing a dictionary for each registry value in the key
    #  "sub_keys" is a list containing one entry for each sub_key
    def list_registry_keys_and_values(self, regkey):
        data = {"name": "reg enum key", "object": regkey}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        results = {}
        results["values"] = self._poll_command(command_id).get("values", [])
        results["sub_keys"] = self._poll_command(command_id).get("sub_keys", [])
        return results

    # returns a list containing a dictionary for each registry value in the key
    def list_registry_keys(self, regkey):
        data = {"name": "reg enum key", "object": regkey}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        return self._poll_command(command_id).get("values", [])

    # returns a dictionary with the registry value
    def get_registry_value(self, regkey):
        data = {"name": "reg query value", "object": regkey}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        return self._poll_command(command_id).get("value", {})

    def set_registry_value(self, regkey, value, overwrite=True, value_type=None):
        if value_type is None:
            if type(value) == int:
                value_type = "REG_DWORD"
            elif type(value) == list:
                value_type = "REG_MULTI_SZ"
            # elif type(value) == bytes:
            #     value_type = "REG_BINARY"
            else:
                value_type = "REG_SZ"
                value = str(value)

        data = {"name": "reg set value", "object": regkey, "overwrite": overwrite, "value_type": value_type,
                "value_data": value}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        self._poll_command(command_id)

    def create_registry_key(self, regkey):
        data = {"name": "reg create key", "object": regkey}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        self._poll_command(command_id)

    def delete_registry_key(self, regkey):
        data = {"name": "reg delete key", "object": regkey}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        self._poll_command(command_id)

    def delete_registry_value(self, regkey):
        data = {"name": "reg delete value", "object": regkey}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')
        self._poll_command(command_id)

    #
    # Physical memory capture
    #
    def memdump(self, local_filename, remote_filename=None, compress=True):
        dump_object = self.start_memdump(remote_filename=remote_filename, compress=compress)
        dump_object.wait()
        dump_object.get(local_filename)
        dump_object.delete()

    def start_memdump(self, remote_filename=None, compress=True):
        if not remote_filename:
            remote_filename = self._random_file_name()

        data = {"name": "memdump", "object": remote_filename, "compress": compress}
        resp = self._lr_post_command(data).json()
        command_id = resp.get('id')

        if compress:
            remote_filename += ".zip"

        return LiveResponseMemdump(self, command_id, remote_filename)

    def _random_file_name(self):
        randfile = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(12)])
        if self.os_type == 1:
            workdir = 'c:\\windows\\carbonblack'
        else:
            workdir = '/tmp'

        return self.path_join(workdir, 'cblr.%s.tmp' % (randfile,))

    def _poll_command(self, command_id, **kwargs):
        return poll_status(self._cb, "/api/v1/cblr/session/{0}/command/{1}".format(self.session_id, command_id),
                           **kwargs)

    def _upload_file(self, fp):
        resp = self._cb.session.post("/api/v1/cblr/session/{0}/file".format(self.session_id), files={"file": fp}).json()
        return resp.get('id')

    def _lr_post_command(self, data):
        retries = self.MAX_RETRY_COUNT

        if "name" in data and data["name"] not in self.session_data["supported_commands"]:
            raise ApiError("Command {0} not supported by this sensor".format(data["name"]))

        while retries:
            try:
                data["session_id"] = self.session_id
                resp = self._cb.post_object("/api/v1/cblr/session/{0}/command".format(self.session_id), data)
            except ObjectNotFoundError as e:
                if e.message.startswith("Sensor") or e.message.startswith("Session"):
                    self.session_id, self.session_data = self._lr_scheduler._get_or_create_session(self.sensor_id)
                    retries -= 1
                    continue
                else:
                    raise ApiError("Received 404 error from server: {0}".format(e.message))
            else:
                return resp

        raise ApiError("Command {0} failed after {1} retries".format(data["name"], self.MAX_RETRY_COUNT))


class LiveResponseMemdump(object):
    def __init__(self, lr_session, memdump_id, remote_filename):
        self.lr_session = lr_session
        self.memdump_id = memdump_id
        self.remote_filename = remote_filename
        self._done = False
        self._error = None

    def get(self, local_filename):
        if not self._done:
            self.wait()
        if self._error:
            raise self._error
        src = self.lr_session.get_raw_file(self.remote_filename, timeout=3600, delay=5)
        dst = open(local_filename, "wb")
        shutil.copyfileobj(src, dst)

    def wait(self):
        self.lr_session._poll_command(self.memdump_id, timeout=3600, delay=5)
        self._done = True

    def delete(self):
        self.lr_session.delete_file(self.remote_filename)


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
                for session in itervalues(self._sessions):
                    if session._refcount == 0:
                        delete_list.append(session.sensor_id)
                    else:
                        try:
                            self._send_keepalive(session.session_id)
                        except ObjectNotFoundError:
                            log.debug("Session {0} for sensor {1} not valid any longer, removing from cache"
                                      .format(session.session_id, session.sensor_id))
                            delete_list.append(session.sensor_id)
                        except:
                            log.debug("Keepalive on session {0} (sensor {1}) failed with unknown error, removing from cache"
                                      .format(session.session_id, session.sensor_id))
                            delete_list.append(session.sensor_id)

                for sensor_id in delete_list:
                    try:
                        session_data = self._cb.get_object("/api/v1/cblr/session/{0}"
                                                           .format(self._sessions[sensor_id].session_id))
                        session_data["status"] = "close"
                        self._cb.put_object("/api/v1/cblr/session/{0}".format(self._sessions[sensor_id].session_id),
                                            session_data)
                    except:
                        pass
                    finally:
                        del self._sessions[sensor_id]

    def request_session(self, sensor_id):
        with self._session_lock:
            if sensor_id in self._sessions:
                session = self._sessions[sensor_id]
                self._sessions[sensor_id]._refcount += 1
            else:
                session_id, session_data = self._get_or_create_session(sensor_id)
                session = LiveResponseSession(self, session_id, sensor_id, session_data=session_data)
                self._sessions[sensor_id] = session

        return session

    def close_session(self, sensor_id):
        with self._session_lock:
            try:
                self._sessions[sensor_id]._refcount -= 1
            except KeyError:
                pass

    def _send_keepalive(self, session_id):
        log.debug("Sending keepalive message for session id {0}".format(session_id))
        self._cb.get_object("/api/v1/cblr/session/{0}/keepalive".format(session_id))

    def _get_or_create_session(self, sensor_id):
        sensor_sessions = [s for s in self._cb.get_object("/api/v1/cblr/session")
                           if s["sensor_id"] == sensor_id and s["status"] in ("pending", "active")]

        if len(sensor_sessions) > 0:
            session_id = sensor_sessions[0]["id"]
        else:
            session_id = self._create_session(sensor_id)

        try:
            res = poll_status(self._cb, "/api/v1/cblr/session/{0}".format(session_id), desired_status="active")
        except ObjectNotFoundError:
            # the Cb server will return a 404 if we don't establish a session in time, so convert this to a "timeout"
            raise TimeoutError("Could not establish session with sensor {0}".format(sensor_id))
        else:
            return session_id, res

    def _create_session(self, sensor_id):
        response = self._cb.post_object("/api/v1/cblr/session", {"sensor_id": sensor_id}).json()
        session_id = response["id"]
        return session_id


class GetFileJob(object):
    def __init__(self, file_name):
        self._file_name = file_name

    def run(self, session):
        return session.get_file(self._file_name)


# TODO: adjust the polling interval and also provide a callback function to report progress
def poll_status(cb, url, desired_status="complete", timeout=None, delay=None):
    start_time = time.time()
    status = None

    if not timeout:
        timeout = 120
    if not delay:
        delay = 0.5

    while status != desired_status and time.time() - start_time < timeout:
        res = cb.get_object(url)
        if res["status"] == desired_status:
            return res
        elif res["status"] == "error":
            raise LiveResponseError(res)
        else:
            time.sleep(delay)

    raise TimeoutError(url, message="timeout polling for Live Response")


if __name__ == "__main__":
    from cbapi.response import CbEnterpriseResponseAPI
    import logging
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())

    logging.getLogger("cbapi").setLevel(logging.DEBUG)

    c = CbEnterpriseResponseAPI()
    j = GetFileJob(r"c:\test.txt")
    with c.select(Sensor, 9).lr_session() as lr_session:
        file_contents = lr_session.get_file(r"c:\test.txt")

    c.live_response.submit_job("test", j.run, [9, ])
    for x in c.live_response.job_results("test"):
        print(x.result())

