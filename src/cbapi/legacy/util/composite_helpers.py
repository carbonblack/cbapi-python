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
# Meant to help in situations where you need Messaging and Live Response.
#
# last updated 2015-05-25 by Ben Johnson bjohnson@bit9.com
#

from live_response_helpers import LiveResponseHelper
from messaging_helpers import QueuedCbSubscriber

class MessageSubscriberAndLiveResponseActor(QueuedCbSubscriber):
    """
    This helper class is for situations where you need to subscribe to messages
    and then connect via live response to grab data or take action.
    """
    def __init__(self, cb_server_url, cb_ext_api, username, password, routing_key):
        self.cb = cb_ext_api
        self.lr_sessions_by_sensor_id = {}
        QueuedCbSubscriber.__init__(self, cb_server_url, username, password, routing_key)

    def _create_lr_session_if_necessary(self, sensor_id):
        """
        Attempt to establish a CB Live Response session if we don't already have one.
        """
        lrh = self.lr_sessions_by_sensor_id.get(sensor_id, None)
        if not lrh:
             lrh = LiveResponseHelper(self.cb, sensor_id)
             lrh.start()
             self.lr_sessions_by_sensor_id[sensor_id] = lrh
        return lrh

    def on_stop(self):
        # Clean up all our live response sessions!!
        for lr in self.lr_sessions_by_sensor_id.values():
            lr.stop()

    def consume_message(self, channel, method_frame, header_frame, body):
        raise Exception("Base class must implement!")

