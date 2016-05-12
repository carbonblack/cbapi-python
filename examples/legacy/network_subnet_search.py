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

        # set up some stat tracking
        self.stats = {}
        self.stats['total_processes'] = 0
        self.stats['total_netconns'] = 0
        self.stats['matching_netconns'] = 0
        self.stats['output_errors'] = 0
        self.stats['process_errors'] = 0

    def getStats(self):
        """
        return the current statistics
        """
        return self.stats

    def outputNetConn(self, proc, netconn):
        """
        output a single netconn event from a process document
        the caller is responsible for ensuring that the document
        meets start time and subnet criteria
        """

        # for convenience, use locals for some process metadata fields
        hostname = proc.get("hostname", "<unknown>")
        process_name = proc.get("process_name", "<unknown>")
        user_name = proc.get("username", "<unknown>")
        process_md5 = proc.get("process_md5", "<unknown>")
        cmdline = proc.get("cmdline", "<unknown>")
        path = proc.get("path", "<unknown>")
        procstarttime = proc.get("start", "<unknown>")
        proclastupdate = proc.get("last_update", "<unknown>")

        # split the netconn into component parts
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

        # print the record, using pipes as a delimiter
        print "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|" % (procstarttime,proclastupdate,hostname, user_name, proto, str_ip, port, dir, domain, process_name, process_md5, path, cmdline)

    def addressInNetwork(self, ip, cidr):

        # the ip can be the emtpy string ('') in cases where the connection
        # is made via a web proxy.  in these cases the sensor cannot report
        # the true remote IP as DNS resolution happens on the web proxy (and
        # not the endpoint)
        if '' == ip:
            return False

        try:
            net = cidr.split('/')[0]
            bits = cidr.split('/')[1]

            if int(ip) > 0: 
                ipaddr = struct.unpack('<L', socket.inet_aton(ip))[0]
            else:
                ipaddr = struct.unpack('<L', socket.inet_aton(".".join(map(lambda n: str(int(ip)>>n & 0xFF), [24,16,8,0]))))[0]
            netaddr = struct.unpack('<L', socket.inet_aton(net))[0]
            netmask = ((1L << int(bits)) - 1)
                
            return ipaddr & netmask == netaddr & netmask

        except:
            return False

    def report(self, result, subnet):

        # return the events associated with this process segment
        # this will include netconns, as well as modloads, filemods, etc.
        events = self.cb.process_events(result["id"], result["segment_id"])
        
        proc = events["process"]

        # the search criteria (netconn_count:[1 to *]) should ensure that
        # all results have at least one netconn
        if proc.has_key("netconn_complete"):

            # examine each netconn in turn
            for netconn in proc["netconn_complete"]:
        
                # update the count of total netconns
                self.stats['total_netconns'] = self.stats['total_netconns'] + 1
        
                # split the netconn event into component parts
                # note that the port is the remote port in the case of outbound
                # netconns, and local port in the case of inbound netconns
                #
                # for the purpose of this example script, eat any errors
                ts, ip, port, proto, domain, dir = netconn.split("|")
                if self.addressInNetwork(ip, subnet): 
                    try:
                        self.stats['matching_netconns'] = self.stats['matching_netconns'] + 1
                        self.outputNetConn(proc, netconn)
                    except:
                        self.stats['output_errors'] = self.stats['output_errors'] + 1
                        pass 

    def strip_to_int(ip):
        """
        convert a dotted-quad string IP to the corresponding int32
        """
        return struct.unpack('<L', socket.inet_aton(ip))[0]

    def check(self, subnet, datetype, begin, end):

        # print a legend
        print "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|" % ("ProcStartTime", "ProcUpdateTime","hostname", "username", "protocol", "ip", "port", "direction", "domain",  "process name",  "process md5", "process path", "cmdline")

        # build the query string
        if not end and not begin:
            q = "ipaddr:%s" % (subnet,) 
        else:
            if not end: end = "*"
            if not begin: begin = "*"
            q = "ipaddr:%s %s:[%s TO %s]" % (subnet, datetype, begin, end)

        # begin with the first result - we'll perform the search in pages 
        # the default page size is 10 (10 results)
        start = 0

        # loop over the entire result set, paging as required
        while True:

            # get the next page of results 
            procs = self.cb.process_search(q, start=start)
            
            # track the total number of matching results
            self.stats['total_processes'] = procs['total_results']

            # if there are no results, we are done paging 
            if len(procs["results"]) == 0:
                break

            # examine each result individually
            # each result represents a single segment of a single process
            #
            # for the purposes of this example script, eat any errors
            #
            for result in procs["results"]:
                try:
                    self.report(result, subnet)
                except Exception, e:
                    self.stats['process_errors'] = self.stats['process_errors'] + 1

            # move forward to the next page 
            start = start + 10

def is_valid_cidr(subnet):
    """
    verifies a subnet string is properly specified in CIDR notation
    """
    try:
        components = subnet.split('/')
        if 2 != len(components):
            return False
        ip = socket.inet_aton(components[0])
        mask = int(components[1])
        return True
    except:
        return False 

def build_cli_parser():
    parser = OptionParser(usage="%prog [options]", description="Dump all network traffic for a specific subnet with optional date range")

    # for each supported output type, add an option
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-S", "--stats", action="store_true", default=False, dest='stats',
                      help="Output stats at end of run.")
    parser.add_option("-s", "--subnet", action="store", default=None, dest="subnet",
                      help="Subnet, as specified in CIDR notation e.g. 127.0.0.1/32, to query for network traffic")
    parser.add_option("-b", "--begin", action="store", default=None, dest="begin",
                      help="Beginning date to start from Format: YYYY-MM-DD")
    parser.add_option("-e", "--end", action="store", default=None, dest="end",
                      help="Beginning date to start from Format: YYYY-MM-DD")                      
    parser.add_option("-t", "--datetype", action="store", default=None, dest="datetype",
                      help="Either Start time or Last Update Time [start|last_update]")                              
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or not opts.subnet :
        print "Missing required param."
        sys.exit(-1)
    if (opts.begin or opts.end ) and not opts.datetype:
        print "You must specify date type if utilizing a date qualifier"
        sys.exit(-1)
    if opts.datetype and (opts.datetype != "start" and opts.datetype != "last_update"):
        print "The date type has to be one of 'start' or 'last_update'"
        sys.exit(-1)
    if not is_valid_cidr(opts.subnet):
        print "The subnet must be in CIDR notation e.g. 192.168.1.0/24"
        sys.exit(-1) 

    cb = CBQuery(opts.url, opts.token, ssl_verify=opts.ssl_verify)

    cb.check(opts.subnet, opts.datetype, opts.begin, opts.end)

    stats = cb.getStats()

    if opts.stats:
        print
        print "%-30s | %s" % ("Total Matching Processes", stats['total_processes'])
        print "%-30s | %s" % ("Total NetConns", stats['total_netconns'])
        print "%-30s | %s" % ("Matching NetConns", stats['matching_netconns'])
        print
        print "%-30s | %s" % ("Processing Errors", stats['process_errors'])
        print "%-30s | %s" % ("Output Errors", stats['output_errors'])
 
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
