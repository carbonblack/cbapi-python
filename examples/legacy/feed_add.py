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
    parser = optparse.OptionParser(usage="%prog [options]", description="Add a new feed to the Carbon Black server")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server_url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-u", "--feed-url", action="store", default=None, dest="feed_url")
    parser.add_option("-v", "--validate_server_cert", action="store_true", default=False, dest="validate_server_cert",
                      help="Carbon Black server will verify the SSL certificate of the feed server")
    parser.add_option("-p", "--use_proxy", action="store_true", default=False, dest="use_proxy",
                      help="Carbon Black server will use configured web proxy to download feed from feed url")
    parser.add_option("-e", "--enabled", action="store_true", default=False, dest="enabled",
                      help="Enable the feed for immediate matching")
    parser.add_option("-k", "--ssl-client-key", action="store", default=None, dest="ssl_client_key",
                      help="Filename of SSL client private key required to access feed in unencrypted PEM format")
    parser.add_option("-C", "--ssl-client-crt", action="store", default=None, dest="ssl_client_crt",
                      help="Filename of SSL client certificate required to access feed in unencrypted PEM format")
    parser.add_option("-U", "--username", action="store", default=None, dest="feed_username",
                      help="HTTP Basic Authentication username required to access feed")
    parser.add_option("-P", "--password", action="store", default=None, dest="feed_password",
                      help="HTTP Basic Authentication password required to access feed")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.server_url or not opts.token or not opts.feed_url:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.server_url, token=opts.token, ssl_verify=opts.ssl_verify)

    # add the feed.  The feed metadata (name, icon, etc.) will be pulled from
    # the feed itself  
    #

    ssl_client_crt = None
    ssl_client_key = None

    if opts.ssl_client_crt:
        ssl_client_crt = open(opts.ssl_client_crt,'r').read().strip()
    if opts.ssl_client_key:
        ssl_client_key = open(opts.ssl_client_key,'r').read().strip()

    results = cb.feed_add_from_url(opts.feed_url, opts.enabled, opts.validate_server_cert, opts.use_proxy,
                                   opts.feed_username, opts.feed_password, ssl_client_crt, ssl_client_key)

    print
    print "-> Feed added [id=%s]" % (results['id'])
    print "   -------------------------"
    print "   Name     : %s" % (results['name'],)
    print "   Display  : %s" % (results['display_name'],)
    print

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
