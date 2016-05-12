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
#  Extension regmod watcher and grabber
#
#  This script listens to the CB messaging bus for registry modification events, 
#  and when a modification is seen that matches a regular expression from a file 
#  of registry path regular expressions, it goes and grabs the registry value 
# using CB Live Response.
#
#  You need to make sure rabbitmq is enabled in cb.conf, and you might need to
#  open a firewall rule for port 5004.  You also will need to enable regmod
#  in the DatastoreBroadcastEventTypes=<values> entry.  If anything is changed
#  here, you'll have to do service cb-enterprise restart.
#
#  TODO: More error handling, more performance improvements
#
#  last updated 2016-01-23 by Ben Johnson bjohnson@bit9.com (dev-support@bit9.com)
#

import Queue
import re
import sys
import time
import traceback
from threading import Thread

import cbapi.util.sensor_events_pb2 as cpb
from cbapi.util.composite_helpers import MessageSubscriberAndLiveResponseActor

from cbapi.legacy.util.cli_helpers import main_helper


class RegistryModWatcherAndValueGrabber(MessageSubscriberAndLiveResponseActor):
    """
    This class subscribes to messages from the CB messaging bus,
    looking for regmod events.  For each regmod event, it checks
    to see if the the registry path matches one of our regexes.
    If it does, it goes and grabs it.
    """
    def __init__(self, cb_server_url, cb_ext_api, username, password, regmod_regexes, verbose):
        self.regmod_regexes = regmod_regexes
        self.verbose = verbose
        MessageSubscriberAndLiveResponseActor.__init__(self,
                                                       cb_server_url,
                                                       cb_ext_api,
                                                       username,
                                                       password,
                                                       "ingress.event.regmod")

        # Threading so that message queue arrives do not block waiting for live response
        self.queue = Queue.Queue()
        self.go = True
        self.worker_thread = Thread(target=self._worker_thread_loop)
        self.worker_thread.start()

    def on_stop(self):
        self.go = False
        self.worker_thread.join(timeout=2)
        MessageSubscriberAndLiveResponseActor.on_stop(self)

    def consume_message(self, channel, method_frame, header_frame, body):
        if "application/protobuf" != header_frame.content_type:
            return

        try:
            # NOTE -- this is not very efficient in PYTHON, and should
            # use a C parser to make this much, much faster.
            # http://yz.mit.edu/wp/fast-native-c-protocol-buffers-from-python/
            x = cpb.CbEventMsg()
            x.ParseFromString(body)
            if not x.regmod or x.regmod.action != 2:
                # Check for MODIFICATION event because we will usually get
                # a creation event and a modification event, and might as
                # well go with the one that says data has actually been written.
                return

            regmod_path = None

            if x.regmod.utf8_regpath:
                if self.verbose:
                    print "Event arrived: |%s|" % x.regmod.utf8_regpath
                for regmod_regex in self.regmod_regexes:
                    if regmod_regex.match(x.regmod.utf8_regpath):
                        regmod_path = x.regmod.utf8_regpath
                        break

            if regmod_path:
                regmod_path = regmod_path.replace("\\registry\\machine\\", "HKLM\\")
                regmod_path = regmod_path.replace("\\registry\\user\\", "HKEY_USERS\\")
                regmod_path = regmod_path.strip()
                # TODO -- more cleanup here potentially?

                self.queue.put((x, regmod_path))

        except:
            traceback.print_exc()

    def _worker_thread_loop(self):
        while self.go:
            try:
                try:
                    (x, regmod_path) = self.queue.get(timeout=0.5)
                except Queue.Empty:
                    continue

                # TODO -- could comment this out if you want CSV data to feed into something
                print "--> Attempting for %s" % regmod_path

                # Go Grab it if we think we have something!
                sensor_id = x.env.endpoint.SensorId
                hostname = x.env.endpoint.SensorHostName

                # TODO -- this could use some concurrency and work queues because we could wait a while for
                # each of these to get established and retrieve the value

                # Establish our CBLR session if necessary!
                lrh = self._create_lr_session_if_necessary(sensor_id)

                data = lrh.get_registry_value(regmod_path)

                print "%s,%s,%d,%s,%s,%s" % ( time.asctime(),
                                              hostname,
                                              sensor_id,
                                              x.header.process_path,
                                              regmod_path,
                                              data.get('value_data', "") if data else "<UNKNOWN>")

                # TODO -- could *do something* here, like if it is for autoruns keys then go check the signature status
                # of the binary at the path pointed to, and see who wrote it out, etc
            except:
                traceback.print_exc()


def main(cb, args):
    username = args.get("username")
    password = args.get("password")
    regpaths_file = args.get("regpaths_file")
    verbose = args.get("verbose", False)
    if verbose:
        # maybe you want to print out all the regpaths we're using?
        print "Regpaths file:", regpaths_file

    f = file(regpaths_file, 'rb')
    regpaths_data = f.read()
    f.close()
    regmod_regexes = []
    for line in regpaths_data.split('\n'):
        line = line.strip()
        if len(line) == 0:
            continue
        regmod_regexes.append(re.compile(line))


    listener = RegistryModWatcherAndValueGrabber(args.get('server_url'), cb, username, password, regmod_regexes, verbose)

    try:
        if verbose:
            print "Registry Mod Watcher and Grabber -- started.  Watching for:", regpaths_data
        else:
            print "Registry Mod Watcher and Grabber -- started. Watching for %d regexes" % len(regmod_regexes)

        listener.process()
    except KeyboardInterrupt:
        print >> sys.stderr, "Caught Ctrl-C"
        listener.stop()
    print "Registry Mod Watcher and Grabber -- stopped."

if __name__ == "__main__":

    ## YOU CAN USE data/autoruns_regexes.txt to test ##
    
    required_args =[("-i", "--username", "store", None, "username", "CB messaging username"),
                    ("-p", "--password", "store", None, "password", "CB messaging password"),
                    ("-r", "--regpaths_file", "store", None, "regpaths_file", "File of newline delimited regexes for regpaths")]
    optional_args = [("-v", "--verbose", "store_true", False, "verbose", "Enable verbose output")]
    main_helper("Subscribe to message bus events and for each registry modification that matches one of our supplied regexes, go retrieve value.",
                main,
                custom_required=required_args,
                custom_optional=optional_args)
