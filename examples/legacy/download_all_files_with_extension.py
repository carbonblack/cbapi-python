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
#  Extension file watcher and grabber
#
#  This script listens to the CB messaging bus for file modification events, and
#  when a modification is seen that ends in a specified extension, it goes and
#  grabs the file using CB Live Response.
#
#  You need to make sure rabbitmq is enabled in cb.conf, and you might need to
#  open a firewall rule for port 5004.  You also will need to enable filemod
#  in the DatastoreBroadcastEventTypes=<values> entry.  If anything is changed
#  here, you'll have to do service cb-enterprise restart.
#
#  TODO: More error handling, more performance improvements
#
#  last updated 2015-05-25 by Ben Johnson bjohnson@bit9.com
#
import sys
import time
import traceback

import cbapi.util.sensor_events_pb2 as cpb
from cbapi.util.composite_helpers import MessageSubscriberAndLiveResponseActor

from cbapi.legacy.util.cli_helpers import main_helper


class ExtensionFileWatcherAndGrabber(MessageSubscriberAndLiveResponseActor):
    """
    This class subscribes to messages from the CB messaging bus,
    looking for filemod events.  For each filemod event, it checks
    to see if the file ends in .dmp.  If it does, it goes and
    grabs it.
    """
    def __init__(self, cb_server_url, cb_ext_api, username, password, extensions, output_dir):
        self.output_dir = output_dir
        self.extensions = extensions
        MessageSubscriberAndLiveResponseActor.__init__(self,
                                                       cb_server_url,
                                                       cb_ext_api,
                                                       username,
                                                       password,
                                                       "ingress.event.filemod")

    def __generate_filename(self, sensor_id, filemod_path):
        """
        Returns a path that is the concatenation of the output directory and
        the filename, with some effort done to replace characters that might be
        tricky in linux/OSX.
        """
        filename = "%d-%s" % (sensor_id, filemod_path)
        filename = filename.replace(":", "_").replace("\\", "__").replace(" ", "_")
        return filename

    def consume_message(self, channel, method_frame, header_frame, body):
        if "application/protobuf" != header_frame.content_type:
            return

        try:
            # NOTE -- this is not very efficient in PYTHON, and should
            # use a C parser to make this much, much faster.
            # http://yz.mit.edu/wp/fast-native-c-protocol-buffers-from-python/
            x = cpb.CbEventMsg()
            x.ParseFromString(body)

            if not x.filemod or x.filemod.action != 2:
                # Check for MODIFICATION event because we will usually get
                # a creation event and a modification event, and might as
                # well go with the one that says data has actually been written.
                return

            filemod_path = None

            # A little non-ideal but this is how the protobuf is setup
            for s in x.strings:
                if s.string_type == 1: #File Path String
                    for extension in self.extensions:
                        if s.utf8string.endswith(extension):
                            filemod_path = s.utf8string
                            break

            if filemod_path:
                # Go Grab it if we think we have something!

                sensor_id = x.env.endpoint.SensorId
                hostname = x.env.endpoint.SensorHostName

                # Establish our CBLR session if necessary!
                lrh = self._create_lr_session_if_necessary(sensor_id)

                # Grab the data!  # TODO -- what if this is LARGE??
                data = lrh.get_file(filemod_path)

                # Generate a filepath and write it out!
                output_filepath = "%s/%s" % (self.output_dir,
                                             self.__generate_filename(sensor_id, filemod_path))
                fout = open(output_filepath, 'wb')
                fout.write(data)
                fout.close()

                print "%s Received %s(%d) %s (%d bytes) => %s" % (time.asctime(),
                                                                  hostname,
                                                                  sensor_id,
                                                                  filemod_path,
                                                                  len(data),
                                                                  output_filepath)
        except:
            traceback.print_exc()


def main(cb, args):

    username = args.get("username")
    password = args.get("password")
    output = args.get("output")
    extensions = args.get("extensions").split(",")


    listener = ExtensionFileWatcherAndGrabber(args.get('server_url'), cb, username, password, extensions, output)

    try:
        print "Extension File Watcher and Grabber -- started.  Watching for:", extensions
        listener.process()
    except KeyboardInterrupt:
        print >> sys.stderr, "Caught Ctrl-C"
        listener.stop()
    print "Extension File Watcher and Grabber -- stopped."

if __name__ == "__main__":
    required_args =[("-i", "--username", "store", None, "username", "CB messaging username"),
                    ("-p", "--password", "store", None, "password", "CB messaging password"),
                    ("-e", "--extensions", "store", None, "extensions", "Extensions to watch for (e.g .dmp, .vbs), comma-delimited"),
                    ("-o", "--output", "store", None, "output", "Output directory for captured files")]

    main_helper("Subscribe to message bus events and for each file with specified extension, go retrieve it.",
                main,
                custom_required=required_args)
