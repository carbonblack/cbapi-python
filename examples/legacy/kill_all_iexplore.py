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
#  <Short Description>
#
#  <Long Description>
#
#  last updated 2015-06-28 by Ben Johnson bjohnson@bit9.com
#

from cbapi.util.cli_helpers import main_helper

from cbapi.legacy.util.live_response_helpers import LiveResponseHelper


def main(cb, args):
    sensor_id = int(args.get('sensorid'))
    lrh = LiveResponseHelper(cb, sensor_id)
    lrh.start()

    # THIS COULD EASILY BE TURNED INTO A LOOP SO THAT YOU CONTINUOUSLY POLL FOR A SPECIFIC PROCESS AND KILL IT
    processes = lrh.process_list()
    for process in processes:
        path = process.get('path')
        if path.lower().endswith('iexplore.exe'):
            lrh.kill(process.get('pid'))
            print "Killed: %s|%s|%s" % (process.get('path'),
                                        process.get('command_line', ''),
                                        process.get('username', ''))

    lrh.stop()

if __name__ == "__main__":
    required_arg = ("-s", "--sensorid", "store", None, "sensorid", "Sensor id")
    main_helper("Kill all iexplore.exe processes on particular sensor", main, custom_required=[required_arg])
