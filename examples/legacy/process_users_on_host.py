#!/usr/bin/env python
#
#The MIT License (MIT)
##
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
# USAGE: python process_users_on_host.py -c https://127.0.0.1:443 -a 167b2587fbc3f6c0c488ab3ddd9d370fdb3f3dcb -n -H WIN-N15HDTS50LK
#
# EXAMPLE OUTPUT:
#
# USER REPORT FOR WIN-N15HDTS50LK:
# --------------------------------------------
# NEW USER found on WIN-N15HDTS50LK : NETWORK SERVICE
# NEW USER found on WIN-N15HDTS50LK : SYSTEM
# NEW USER found on WIN-N15HDTS50LK : LOCAL SERVICE
# NEW USER found on WIN-N15HDTS50LK : WIN-N15HDTS50LK\BTedesco
# NEW USER found on WIN-N15HDTS50LK : (unknown)
#
# Hostname | Process Count : Username
# --------------------------------------------
# WIN-N15HDTS50LK | 136 = WIN-N15HDTS50LK\BTedesco
# WIN-N15HDTS50LK | 43 = (unknown)
# WIN-N15HDTS50LK | 32 = NETWORK SERVICE
# WIN-N15HDTS50LK | 1487 = SYSTEM
# WIN-N15HDTS50LK | 27 = LOCAL SERVICE
#
#  <Long Description>
#
#  last updated 2015-12-10 by Ben Tedesco btedesco@bit9.com
#

import sys
import struct
import socket
from optparse import OptionParser
from cbapi import CbApi

class CBQuery(object):
    def __init__(self, url, token, ssl_verify):
        self.cb = CbApi(url, token=token, ssl_verify=ssl_verify)
        self.cb_url = url

    def report(self, hostname, user_dictionary):
        print ""
        print "%s | %s : %s" % ("Hostname", "Process Count", "Username")
        print "--------------------------------------------"
 
	for key,value in user_dictionary.items():
		print "%s | %s = %s" % (hostname, value, key)

    def check(self, hostname):
        # print a legend
	print ""
	print "USER REPORT FOR %s:" % (hostname)
	print "--------------------------------------------"

        # build the query string
        q = "hostname:%s" % (hostname)
      
	#define dictionary
	user_dictionary = dict()
 
	# loop over the entire result set
        for result in self.cb.process_search_iter(q):
		user_name = result.get("username", "<unknown>")

		if user_name not in user_dictionary.keys():
			print "NEW USER found on %s : %s" % (hostname, user_name)
			user_dictionary[user_name] = 1
		else:
			user_dictionary[user_name] = user_dictionary[user_name] + 1

	self.report(hostname, user_dictionary)

def build_cli_parser():
    parser = OptionParser(usage="%prog [options]", description="Dump all usernames & associated process counts for given host.")

    # for each supported output type, add an option
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., https://127.0.0.1:443")
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
