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
    print "%s,%s,%s,%s,%s,%s" % ("hostname", "username", "start", "parent_path", "path", "cmdline")
    for (proc, proc_details, parent_details) in \
            cb.process_search_and_detail_iter(
                   'start:%s process_name:net.exe -cmdline:"net stop" -cmdline:"net files" -cmdline:"net sessions"' % start):

            print "%s,%s,%s,%s,%s,%s" % (proc.get('hostname'),
                                         proc.get('username'),
                                         proc.get('start'),
                                         parent_details.get('path'),
                                         proc.get('path'),
                                         proc_details.get('cmdline'))

if __name__ == "__main__":
    required_arg = ("-s", "--start", "store", None, "start", "Process start time to query for, example, -2h for any net.exe processes started in past 2 hours")
    main_helper("Search for net.exe processes", main, custom_required=[required_arg])
