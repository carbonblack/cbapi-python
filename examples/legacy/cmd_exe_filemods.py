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
    for (proc, events) in cb.process_search_and_events_iter(r"process_name:cmd.exe (filemod:*.exe or filemod:*.dll)"):
        filemods = events.get('process', {}).get('filemod_complete', [])
        for filemod in filemods:

            print filemod
            # TODO -- figure out fields
            action, timestamp, filepath, md5, junk1, junk2 = filemod.split('|')

            filepath = filepath.lower()
            if not filepath.endswith(".exe") or not filepath.endswith(".dll"):
                continue

            if action == "1":
                action = "CREATE"
            elif action == "2":
                action = "MODIFY"
            elif action == "4":
                action = "DELETE"
            elif action == "8":
                action = "EXECUTABLE_WRITE"

            print "%s,%s,%s,%s,%s,%s" % (timestamp, proc['hostname'], proc['username'], proc['path'], filepath, action)

if __name__ == "__main__":
    main_helper("Search for cmd.exe writing to exe and dll filepaths", main)
