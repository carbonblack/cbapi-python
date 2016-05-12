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
import optparse
import cbapi 

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Configure SSL client certificate authentication for feeds")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server_url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-i", "--id", action="store", default=None, dest="id",
                      help="Feed Id")
    parser.add_option("-r", "--remove", action="store_true", default=False, dest="remove",
                      help="Remove SSL client certificate authentication for the feed specified with -i")
    parser.add_option("-C", "--certificate", action="store", default=None, dest="certificate",
                      help="SSL client certificate filename; expected to begin with \"-----BEGIN CERTIFICATE-----\"")
    parser.add_option("-K", "--key", action="store", default=None, dest="key",
                      help="SSL client key filename; expected to begin with \"-----BEGIN RSA PRIVATE KEY-----\"") 
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)

    if not opts.server_url or not opts.token:
        print "Must specify a CB server and API token with -c and -a"
        sys.exit(-1)

    if not opts.id:
        print "Must specify a feed id"
        sys.exit(-1)

    if not opts.remove and not (opts.certificate and opts.key):
      print "Missing required param; run with --help for usage"
      print "Either -C AND -K must be specified (to add SSL client certificates to a feed) or -r must be specified"
      sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.server_url, token=opts.token, ssl_verify=opts.ssl_verify)

    feed = {"id": opts.id}

    if opts.remove:
        feed["ssl_client_crt"] = "" 
        feed["ssl_client_key"] = "" 
    else:
        feed["ssl_client_crt"] = open(opts.certificate).read().strip()
        feed["ssl_client_key"] = open(opts.key).read().strip()

    cb.feed_modify(opts.id, feed)

    print "-> Success!"

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
