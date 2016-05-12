import threading
import time
import requests
import json
import random
import string


# TODO/NOTE: this is not the intended "new" API. Just putting this here for now.


class LiveResponseError(Exception):
    pass


class LiveResponseThread(threading.Thread):
    """ note that timeout is not currently implemented """
    def __init__(self, cb, logger, sensor_id):
        self.cb = cb
        self.logger = logger
        self.sensor_id = sensor_id
        self.result_available = False
        self.result = None
        self.done = False
        self.live_response_session = None
        self.newest_time_stamp = time.time()
        self.one_time = True

        threading.Thread.__init__(self)

    def timed_out(self):
        return not self.is_alive() and not self.done

    def stop(self):
        self.done = True

    def establish_session(self):
        self._establish_live_response_session()
        return self.live_response_session

    def _establish_live_response_session(self):
        resp = self.cb.live_response_session_create(self.sensor_id)
        session_id = resp.get('id')

        session_state = 'pending'
        while session_state != 'active':
            time.sleep(5)
            session_state = self.cb.live_response_session_status(session_id).get('status')
            self.logger.debug('LR status=%s' % session_state)

        self.logger.debug('I have a live response session: session_id=%d status=%s' % (session_id, session_state))

        self.live_response_session = session_id

    def _kill_process(self, pid):
        session_id = self.live_response_session
        resp = self.cb.live_response_session_command_post(session_id, "kill", pid)
        command_id = resp.get('id')
        killed = False
        count = 0

        self.logger.warn("Killing %d" % pid)

        while not killed and count < 5:
            resp = self.cb.live_response_session_command_get(session_id, command_id)
            if resp.get('status') == 'complete':
                killed = True
            count += 1
            time.sleep(.1)

        return killed

    def _kill_processes(self, target_proc_guids):
        session_id = self.live_response_session
        killed = []

        resp = self.cb.live_response_session_command_post(session_id, "process list")
        command_id = resp.get('id')

        command_state = 'pending'

        while command_state != 'complete':
            resp = self.cb.live_response_session_command_get(session_id, command_id)
            command_state = resp.get('status')
            time.sleep(.1)

        live_procs = resp.get('processes')
        for live_proc in live_procs:
            live_proc_guid = live_proc.get('proc_guid')
            if live_proc_guid in target_proc_guids:
                live_proc_pid = live_proc.get('pid')
                if self._kill_process(live_proc_pid):
                    self.logger.warn("KILLED %d" % live_proc_pid)
                    killed.append(live_proc_guid)

        return (len(live_procs) > 0), killed

    def get_processes(self):
        session_id = self.live_response_session
        resp = self.cb.live_response_session_command_post(session_id, "process list")
        command_id = resp.get('id')

        command_state = 'pending'

        while command_state != 'complete':
            resp = self.cb.live_response_session_command_get(session_id, command_id)
            command_state = resp.get('status')
            time.sleep(.1)

        live_procs = resp.get('processes')
        return live_procs

    def get_file(self, filename):
        session_id = self.live_response_session
        resp = self.cb.live_response_session_command_post(session_id, "get file", filename)
        file_id = resp.get('file_id')
        command_id = resp.get('id')
        command_state = 'pending'
        while command_state != 'complete':
            time.sleep(.2)
            resp = self.cb.live_response_session_command_get(session_id, command_id)
            command_state = resp.get('status')
        file_content = self.cb.live_response_session_command_get_file(session_id, file_id)
        return file_content

    def create_process(self, command_string):
        # process is:
        # - create a temporary file name
        # - create the process, writing output to a temporary file
        # - wait for the process to complete
        # - get the temporary file from the endpoint
        # - delete the temporary file

        randfile = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(12)])
        workdir = 'c:\\windows\\carbonblack'
        randfilename = '%s\\cblr.%s.tmp' % (workdir, randfile)

        session_id = self.live_response_session

        url = "%s/api/v1/cblr/session/%d/command" % (self.cb.server, session_id)
        data = {"session_id": session_id, "name": "create process", "object": command_string,
                "wait": True, "working_directory": workdir, "output_file": randfilename}
        r = requests.post(url, headers=self.cb.token_header, data=json.dumps(data), verify=self.cb.ssl_verify,
                          timeout=120)
        r.raise_for_status()
        resp = r.json()

        command_id = resp.get('id')
        command_state = 'pending'

        while command_state != 'complete':
            time.sleep(.2)
            resp = self.cb.live_response_session_command_get(session_id, command_id)
            command_state = resp.get('status')

        # now the file is ready to be read

        file_content = self.get_file(randfilename)
        # delete the file
        self.cb.live_response_session_command_post(session_id, "delete file", randfilename)

        return file_content