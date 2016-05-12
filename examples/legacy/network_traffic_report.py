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
import sys
import struct
import socket
from optparse import OptionParser
from cbapi import CbApi

class CBQuery(object):
    def __init__(self, url, token, ssl_verify):
        self.cb = CbApi(url, token=token, ssl_verify=ssl_verify)
        self.cb_url = url

    def report(self, hostname, result):
        
        # return the events associated with this process segment
        # this will include netconns, as well as modloads, filemods, etc.
        events = self.cb.process_events(result["id"], result["segment_id"])
        
        proc = events["process"]

        # for convenience, use locals for some process metadata fields
        process_name = result.get("process_name", "<unknown>")
        user_name = result.get("username", "<unknown>")
        process_md5 = result.get("process_md5", "<unknown>")

        # the search criteria (netconn_count:[1 to *]) should ensure that
        # all results have at least one netconn
        if proc.has_key("netconn_complete"):

            # examine each netconn in turn
            for netconn in proc["netconn_complete"]:

                # split the netconn event into component parts
                # note that the port is the remote port in the case of outbound
                # netconns, and local port in the case of inbound netconns
                ts, ip, port, proto, domain, dir = netconn.split("|")
                
                # get the dotted-quad string representation of the ip
                str_ip = socket.inet_ntoa(struct.pack("!i", int(ip)))
                
                # the underlying data model provides the protocol number
                # convert this to human-readable strings (tcp or udp)
                if "6" == proto:
                    proto = "tcp"
                elif "17" == proto:
                    proto = "udp"
               
                # the underlying data model provides a boolean indication as to
                # if this is an inbound or outbound network connection 
                if "true" == dir:
                    dir = "out"
                else:
                    dir = "in" 

                # pring the record, using pipes as a delimiter
                print "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s)" % (hostname, ts, process_name, user_name, process_md5, proto, str_ip, port, dir, domain)

    def check(self, hostname):

        # print a legend
        print "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s)" % ("hostname", "timestamp", "process name", "username", "process md5", "protocol", "ip", "port", "direction", "domain")

        # build the query string
        q = "netconn_count:[1 to *] AND hostname:%s" % (hostname)
      
        # begin with the first result - we'll perform the search in pages 
        # the default page size is 10 (10 reslts)
        start = 0

        # loop over the entire result set
        while True:

            # get the next page of results 
            procs = self.cb.process_search(q, start=start)
      
            # if there are no results, we are done paging 
            if len(procs["results"]) == 0:
                break

            # examine each result individually
            # each result represents a single process segment
            for result in procs["results"]:
                self.report(hostname, result)

            # move forward to the next page 
            start = start + 10


def build_cli_parser():
    parser = OptionParser(usage="%prog [options]", description="dump all network connections for a given host to file")

    # for each supported output type, add an option
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-H", "--hostname", action="store", default=None, dest="hostname",
                      help="Endpoint hostname to query for network traffic")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or not opts.hostname:
        print "Missing required param."
        sys.exit(-1)

    cb = CBQuery(opts.url, opts.token, ssl_verify=opts.ssl_verify)

    cb.check(opts.hostname)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
