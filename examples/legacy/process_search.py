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

import pprint

from cbapi.legacy.util.cli_helpers import main_helper


def main(cb, args):

    # perform a single process search
    #
    processes = cb.process_search(args.get('query'))
    
    print "%-20s : %s" % ('Displayed Results', len(processes['results']))
    print "%-20s : %s" % ('Total Results', processes['total_results'])
    print "%-20s : %sms" % ('QTime', int(1000*processes['elapsed']))
    print '\n'

    # for each result 
    for process in processes['results']:
        pprint.pprint(process)
        print '\n'

if __name__ == "__main__":
    required_arg = ("-q", "--query", "store", None, "query", "Process search query")
    main_helper("Generic process search", main, custom_required=[required_arg])