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
#  The purpose of this script is to get the smallest frequency or percentage of a given process
#  child processes.  Once you specify less than x percentage it will walk that process
#  all the way down.
#
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
    parser = OptionParser(usage="%prog [options]", description="Allows for the ability to check the frequency of child process based on a given parent process")

    # for each supported output type, add an option
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-p", "--percentage", action="store", default="2", dest="percentless",
                      help="Max Percentage of Term Frequency e.g., 2 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-t", "--term", action="store", default=None, dest="procname",
                      help="Comma separated list of parent processes to get term frequency")
    parser.add_option("-f", "--termfile", action="store", default=None, dest="procnamefile",
                      help="Text file new line separated list of parent processes to get term frequency")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    return parser


def processsearchlist(procnamefile):
	with open(procnamefile) as tmp:
		lines = [line.rstrip('\n') for line in tmp]
	return lines

def getchildprocs(results):
	for b in results:
		bst, bid, bmd5, bpath, bpid, bcom, bblah = b.split("|")
		q = 'process_id:%s' % (bid)
		if "true" == bcom:
			cdata = cb.process_search(q, start=0)
			for c in cdata['results']:
				getproc(c['id'],c['segment_id'])

def getproc( procid, procseg):
	procdata = cb.process_events(procid,procseg)
	bprocess = procdata['process']
	myrow.append(bprocess["id"]) 
	if bprocess.has_key("cmdline"):
		cmdline = bprocess["cmdline"]
	else:
		cmdline = ""
	myrow.append(cmdline)
	if bprocess.has_key("childproc_complete"):
		getchildprocs(bprocess['childproc_complete'])

parser = build_cli_parser()
opts, args = parser.parse_args(sys.argv[1:])
if not opts.server or not opts.token or (not opts.procnamefile and not opts.procname) or not opts.percentless:
	print "Missing required param."
	sys.exit(-1)

cb = CbApi(opts.server, ssl_verify=opts.ssl_verify, token=opts.token)
if opts.procnamefile:
	searchprocess = processsearchlist(opts.procnamefile)
else:
	searchprocess = opts.procname.split(",")
for proc in searchprocess:
	start = 0
	data = cb.process_search("parent_name:%s" % (proc), rows=1, start=start)
	facetterms = data['facets']
	for term in reversed(facetterms['process_name']):
		termratio = int(float(term['ratio']))
		if int(opts.percentless) >= termratio:
			start = 0
			while True:
				q = "parent_name:%s AND process_name:%s" % (proc,term['name'])
				data = cb.process_search(q , rows=int(pagesize), start=start)
				if 0 == len(data['results']):
					break
				for a in data['results']:
					myrow = []
					parent = proc
					hostname = a["hostname"]
					username = a["username"]
					id = a['id']
					segid = a['segment_id']
					idurl = "%s/#analyze/%s/%s" % (opts.server, id, segid)
					myrow.append(parent)
					myrow.append(term['name'])
					myrow.append(str(term['value']))
					myrow.append(str(term['ratio']))
					myrow.append(q)
					myrow.append(hostname)
					myrow.append(username)
					myrow.append(idurl)
					getproc(a['id'],a['segment_id'])
					print "'"+"','".join(myrow)+"'"
				start = start + int(pagesize)
