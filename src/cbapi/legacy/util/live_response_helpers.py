#!/usr/bin/env python
#
#The MIT License (MIT)
#
# Copyright (c) 2015 Bit9 + Carbon Black
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# -----------------------------------------------------------------------------
# Class for wrapping around Live Response connectivity and actions.
#
# TODO -- more actions wrapped, more error handling, potentially more post-processing
# of returned results?
#
# last updated 2015-05-25 by Ben Johnson bjohnson@bit9.com
#

import threading
import time


class LiveResponseHelper(threading.Thread):
    """
    Threaded class that should do a keep-alive and handle the establishing of
    the live response session.
    """
    def __init__(self, ext_cbapi, sensor_id):
        self.cb = ext_cbapi
        self.sensor_id = sensor_id
        self.session_id = None
        self.keep_alive_time = 60
        self.go = True
        self.ready_event = threading.Event()
        self.ready_event.clear()
        threading.Thread.__init__(self)

    ###########################################################################

    def __create_session(self):
        target_session = self.cb.live_response_session_create(self.sensor_id)
        self.session_id = target_session.get('id')
        while target_session.get('status') == "pending":
            # could make this configurable to only wait certain number
            # of seconds or at least configure how many seconds at a
            # time to wait.
            time.sleep(5.0)

            target_session = self.cb.live_response_session_status(self.session_id)
            if not self.go:
                break

    def __post_and_wait(self, command, command_object=None):
        resp = self.cb.live_response_session_command_post(self.session_id, command, command_object)
        # TODO -- handle errors
        command_id = resp.get('id')
        return self.cb.live_response_session_command_get(self.session_id, command_id, wait=True)

    ###########################################################################

    def run(self):
        # THIS THREAD IS FOR KEEP-ALIVE
        self.__create_session()
        self.ready_event.set()

        while self.go:
            self.cb.live_response_session_keep_alive(self.session_id)
            for i in xrange(self.keep_alive_time):
                # sleep for a second just to wait up to make sure we weren't
                # told to stop
                time.sleep(1.0)
                if not self.go:
                    break

    def stop(self, wait=True):
        self.go = False
        if wait:
            self.join()

    ###########################################################################

    def process_list(self):
        """
        Returns list of dictionaries containing information about each running process.
        """
        self.ready_event.wait()
        return self.__post_and_wait("process list").get('processes', [])

    def kill(self, pid):
        """
        Kills pid on target
        """
        self.ready_event.wait()
        return self.__post_and_wait("kill", pid)

    def get_file(self, filepath):
        """
        Returns file data for <filepath> on sensor's host.
        """
        self.ready_event.wait()
        ret = self.__post_and_wait("get file", filepath)
        fileid = ret["file_id"]
        return self.cb.live_response_session_command_get_file(self.session_id, fileid)

    def put_file(self, rfile, lfile):
        """
        Uploads file data from <lfile> to <rfile> on sensor
        """
        self.ready_event.wait()
        fileid = {'file_id':self.cb.live_response_session_command_put_file(self.session_id, lfile)}
        return self.__post_and_wait("put file", [rfile, fileid])
    

    def del_file(self, filepath):
        """
        Deletes file from target
        """
        self.ready_event.wait()
        return self.__post_and_wait("delete file", filepath)


    def execute(self, procpath, wait_opt=None):
        """
        Creates process on target
        """
        self.ready_event.wait()
        return self.__post_and_wait("create process", procpath)


    def get_registry_value(self, registry_path):
        """
        Retrieve the data from a registry value.
        """
        self.ready_event.wait()
        ret = self.__post_and_wait("reg query value", registry_path)
        return ret.get('value', None)