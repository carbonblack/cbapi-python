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

# in the github repo, cbapi is not in the example directory

from cbapi.legacy.util.cli_helpers import main_helper

def main(cb, args):

    input_file = args.get('inputfile')

    f = file(input_file, "rb")
    lines = f.read().split("\r")

    for line in lines:
        filepath = line.strip()
        if len(filepath) == 0:
            continue

        for (proc, events) in cb.process_search_and_events_iter("filemod:%s" % filepath):
            hostname = proc.get('hostname')
            for filemod in events.get('filemod_complete', []):
                print filemod

            print "%s, %s, %s" % (hostname, proc.get('path'), filepath)

if __name__ == "__main__":
    required_arg = ("-i", "--inputfile", "store", None, "inputfile", "List of filemod paths to search for")
    main_helper("Search for processes modifying particular filepaths", main, custom_required=[required_arg])
