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
import struct
import socket
from optparse import OptionParser
from cbapi import CbApi

# if you run this in a cron job, 
# put the interval here.  This uses the format
# In the last xxx minutes format.  The parser accepts
# h, m or s suffixes.

#CRON_INTERVAL = "24h"
CRON_INTERVAL = None

class CBQuery(object):
    def __init__(self, url, token, ssl_verify):
        self.cb = CbApi(url, token=token, ssl_verify=ssl_verify)
        self.cb_url = url

    def report(self, ioc, type, procs, detail=False):
        for result in procs["results"]:
            # print the results to stdout. you could do anything here - 
            # log to syslog, send a SMS, fire off a siren and strobe light, etc.
            print
            print "Found %s IOC for %s in:" % (type, ioc)
            print
            print "\tPath: %s"          % result["path"]
            print "\tHostname: %s"      % result["hostname"]
            print "\tStarted: %s"       % result["start"]
            print "\tLast Updated: %s"  % result["last_update"]
            print "\tDetails: %s/#analyze/%s/%s" % (self.cb_url, result["id"], result["segment_id"])
            print

            if detail:
                self.report_detail(ioc, type, result)

    def report_detail(self, ioc, type, result):
        events = self.cb.process_events(result["id"], result["segment_id"])
        proc = events["process"]

        if type == "domain" and proc.has_key("netconn_complete"):
            for netconn in proc["netconn_complete"]:
                ts, ip, port, proto, domain, dir = netconn.split("|")
                if ioc in domain:
                    str_ip = socket.inet_ntoa(struct.pack("!i", int(ip)))
                    print "%s\t%s (%s:%s)" % (ts, domain, str_ip, port)

        elif type == "ipaddr" and proc.has_key("netconn_complete"):
            for netconn in proc["netconn_complete"]:
                ts, ip, port, proto, domain, direction = netconn.split("|")
                packed_ip = struct.unpack("!i", socket.inet_aton(ioc))[0]
                #import code; code.interact(local=locals())
                if packed_ip == int(ip):
                    str_ip = socket.inet_ntoa(struct.pack("!i", int(ip)))
                    print "%s\t%s (%s:%s)" % (ts, domain, str_ip, port)

        elif type == "md5" and proc.has_key("modload_complete"):
            for modload in proc["modload_complete"]:
                ts, md5, path = modload.split("|")
                if ioc in md5:
                    print "%s\t%s %s" % (ts, md5, path)

            if result["process_md5"] == ioc:
                print "%s\t%s %s" % (result["start"], result["process_md5"], result["path"])

    def check(self, iocs, type, detail=False):
        # for each ioc, do a search for (type):(ioc)
        # e.g, 
        #   domain:bigfish.com
        #   md5:ce7a81ceccfa03e5e0dfd0d9a7f41466
        # 
        # additionally, if a cron interval is specified, limit searches
        # to processes updated in the last CRON_INTERVAL period
        # 
        # note - this is a very inefficient way to do this, since you test only one
        # IOC per request - you could build a large OR clause together with a few hundred
        # to efficiently and quickly check 1000s of IOCs, at the cost of increased complexity
        # when you discover a hit.
        #
        # note 2 - with a list of flat indicators, what you really want is a CB feed
        # see http://github.com/carbonblack/cbfeeds
        #
        for ioc in iocs:
            if CRON_INTERVAL:
                q = "%s:%s and last_update:-%s" % (type, ioc, CRON_INTERVAL)
            else:
                q = "%s:%s" % (type, ioc)
            print q
            procs = self.cb.process_search(q)

            # if there are _any_ hits, give us the details.
            # then check the next ioc
            if len(procs["results"]) > 0:
                self.report(ioc, type, procs, detail)
            else:
                sys.stdout.write(".")
                sys.stdout.flush()

def build_cli_parser():
    parser = OptionParser(usage="%prog [options]", description="check Cb index for provided IOCs")

    # for each supported output type, add an option
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-f", "--file", action="store", default=None, dest="fname",
                      help="Filename with CRLF-delimited list of IOCs")
    parser.add_option("-t", "--type", action="store", default=None, dest="type",
                      help="Type of IOCs in the file.  Must be one of md5, domain or ipaddr")
    parser.add_option("-d", "--detail", action="store_true", default=False, dest="detail",
                      help="Get full detail about each IOC hit.")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or not opts.fname or not opts.type:
        print "Missing required param."
        sys.exit(-1)

    if not opts.type in ["md5", "domain", "ipaddr"]:
        print "Unknown type: ", opts.type
        sys.exit(-1)

    # setup the CbApi object
    cb = CBQuery(opts.url, opts.token, ssl_verify=opts.ssl_verify)

    # get the IOCs to check; this is a list of strings, one indicator
    # per line.  strip off the newlines as they come in
    vals = [val.strip() for val in open(opts.fname, "r")]

    # check each!
    cb.check(vals, opts.type, opts.detail)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
