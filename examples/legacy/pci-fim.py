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

import sys
from optparse import OptionParser
from cbapi import CbApi

class CBQuery(object):
    def __init__(self, url, token, ssl_verify):
        self.cb = CbApi(url, token=token, ssl_verify=ssl_verify)
        self.cb_url = url

    def report(self, result, search_filename):
        
        # return the events associated with this process segment
        # this will include netconns, as well as modloads, filemods, etc.
        #
        events = self.cb.process_events(result["id"], result["segment_id"])
        
        proc = events["process"]

        # for convenience, use locals for some process metadata fields
        #
        host_name = result.get("hostname", "<unknown>")
        process_name = result.get("process_name", "<unknown>")
        user_name = result.get("username", "<unknown>")

        if proc.has_key("filemod_complete"):

            # examine each filemod in turn
            #
            for filemod in proc["filemod_complete"]:

                # filemods are of the form:
                #   1|2014-06-19 15:40:05.446|c:\dir\filename||
                #
                parts = filemod.split('|')
                action, ts, filename, filemd5, filetype = parts[:5]

                # the _document as a whole_ matched the query
                # that doesn't mean each _indvidual filemod_ within the document matched
                # the user-specified filename to search for
                #
                # iterate over each filemod and determine if the path matches
                # what was specified
                #
                # make sense?  hope so!
                #
                if search_filename.lower() not in filename.lower():
                    continue 

                if "1" == action:
                    action = "creation"
                elif "2" == action or "8" == action:
                    action = "modification"
                elif "4" == action:
                    action = "deletion"

                print "%s|%s|%s|%s|%s|%s" % (host_name, ts, filename, process_name, user_name, action) 

    def check(self, filename):

        # build the query string
        #
        q = "filemod:%s" % (filename)
      
        # begin with the first result - we'll perform the search in pages 
        # the default page size is 10 (10 reslts)
        #
        start = 0

        # loop over the entire result set
        #
        while True:

            # get the next page of results
            # 
            procs = self.cb.process_search(q, start=start)
      
            # if there are no results, we are done paging 
            #
            if len(procs["results"]) == 0:
                break

            # examine each result individually
            # each result represents a single process segment
            #
            for result in procs["results"]:
                self.report(result, filename)

            # move forward to the next page
            #
            start = start + 10
 
def build_cli_parser():
    parser = OptionParser(usage="%prog [options]", description="Output all file modifications to a set of known filenames.  This can be used in support of PCI compliance for file integrity monitoring.")

    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-f", "--filelist", action="store", default=None, dest="filelist",
                      help="Filename containing list of newline-delimited filenames to check for modifications")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or not opts.filelist:
        print "Missing required command line switch; use -h for usage."
        sys.exit(-1)

    cb = CBQuery(opts.url, opts.token, ssl_verify=opts.ssl_verify)

    # open the "filelist" file and read it's contents
    # this is a newline-delimited file of filenames to be monitored
    # both \n and \r\n line endings are supported
    #
    files = open(opts.filelist).read().split("\n")

    # print a legend
    #
    print "%s|%s|%s|%s|%s|%s" % ("hostname", "timestamp", "filename", "process name", "username", "action")

    # iterate over the list of files, removing any trailing whitespace
    # and searching the CB database for any file modifications to that file
    #
    for file in files:
        file = file.strip()
        if len(file) < 1:
          continue
        cb.check(file)
     
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
