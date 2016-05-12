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

from cbapi.legacy.util.cli_helpers import main_helper

def main(cb, args):
    start = args.get('start')

    for (proc, events) in \
        cb.process_search_and_events_iter(
               'start:%s regmod:registry\\machine\\system\\currentcontrolset\\control\\deviceclasses\\{53f56307-b6bf-11d0-94f2-00a0c91efb8b}\\*' % start):

        for event in events.get('regmod_complete', []):
                fields = event.split('|')
                regpath = fields[2]
                if "{53f56307-b6bf-11d0-94f2-00a0c91efb8b}" in regpath:
                    pieces = regpath.split("usbstor#disk&")
                    if len(pieces) < 2:
                        print "WARN::::", pieces
                    else:
                        device_info = pieces[1] #.split('{53f56307-b6bf-11d0-94f2-00a0c91efb8b}')[0]
                        print device_info

if __name__ == "__main__":
    required_arg = ("-s", "--start", "store", None, "start", "Process start time to query for, example, -2h for any processes started in past 2 hours")
    main_helper("Search for usb device usages", main, custom_required=[required_arg])
