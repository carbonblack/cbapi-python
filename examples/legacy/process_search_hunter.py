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
#  The purpose of this script is to execute a large number of Cb Queries against
#  a Cb server and only display back the queries that have a matching process
#  ***Facets must be enabled and used in the query***
#  by default Facets are enabled on Process Search Queries in Carbon Black
#
#  last updated 2015-11-23
#

import sys
import struct
import socket
import json
from optparse import OptionParser

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')
from cbapi import CbApi
#this is the size of the data returned
pagesize=20

def build_cli_parser():
    parser = OptionParser(usage="%prog [options]", description="Hunt a Carbon Black Server based on a list of queries")

    # for each supported output type, add an option
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-f", "--searchfile", action="store", default=None, dest="procsearchfile",
                      help="File containing a line for each query you would like to run")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    return parser


def processsearchlist(procnamefile):
    with open(procnamefile) as tmp:
        lines = filter(None, [line.strip() for line in tmp])
    return lines

parser = build_cli_parser()
opts, args = parser.parse_args(sys.argv[1:])
if not opts.server or not opts.token or not opts.procsearchfile:
    print "Missing required param."
    sys.exit(-1)

cb = CbApi(opts.server, ssl_verify=opts.ssl_verify, token=opts.token)
searchprocess = processsearchlist(opts.procsearchfile)
for search in searchprocess:
    data = cb.process_search(search, rows=1)
    if 0 != (data['total_results']):
        print "------------------------------"
        print "Search Query | %s" % (search)
        print "Resulting Processes | %s" % (data['total_results'])
        facet=data['facets']
        hosts =[]
        for term in facet['hostname']:
            hosts.append("%s (%s%%)" % (term['name'], term['ratio']))
        print "Resulting Hosts | "+"|".join(hosts)
