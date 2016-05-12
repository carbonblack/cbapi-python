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
#
#  last updated 2015-11-16 by Jason McFarland jmcfarland@bit9.com
#

import sys
import optparse
import cbapi
import urllib
import pprint
import json

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Dump Binary Info")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-f", "--full", action="store_true", default=False, dest="fulloutput",
                      help="Do not truncate watchlist queries in the output")
    parser.add_option("-r", "--rows", action="store", default=10, type="int", dest="numrows",
                      help="number of rows to display")
    parser.add_option("-w", "--watchlistid", action="store", default=None, type="int", dest="watchlistid",
                      help="Enumerate hits from this watchlist id")
    return parser

def truncate(fulloutput, string, length):
    if fulloutput:
        return string
    if len(string) + 2 > length:
        return string[:length] + "..."
    return string

def printWatchlistHits(serverurl, watchlistid, watchlisttype, rows):
    global cb
    pp = pprint.PrettyPrinter(indent=2)

    print rows

    getparams = {"cb.urlver": 1,
                "watchlist_%d" % watchlistid : "*",
                "rows": rows }

    if watchlisttype == 'modules':
        getparams["cb.q.server_added_timestamp"] = "-1440m"
        r = cb.cbapi_get("%s/api/v1/binary?%s" % (serverurl, urllib.urlencode(getparams)))
        parsedjson = json.loads(r.text)
        pp.pprint(parsedjson)

    elif watchlisttype == 'events':
        getparams["cb.q.start"] = "-1440m"
        r = cb.cbapi_get("%s/api/v1/process?%s" % (serverurl, urllib.urlencode(getparams)))
        parsedjson = json.loads(r.text)
        pp.pprint(parsedjson)
    else:
        return

    print
    print "Total Number of results returned: %d" % len(parsedjson['results'])
    print

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    watchlistIds = []

    global cb
    #
    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.url, token=opts.token, ssl_verify=opts.ssl_verify)

    #
    # enumerate all watchlists
    #
    watchlists = cb.watchlist()

    print "%-4s | %-32s |" % ('id', 'name')
    print "%-4s + %-32s +" % ('-' * 4, '-' * 32)

    #
    # for each result
    #
    for watchlist in watchlists:
        print "%-4s | %-32s |" % (watchlist['id'], watchlist['name'] )
        watchlistIds.append(watchlist['id'])
    print "%-4s + %-32s +" % ('-' * 4, '-' * 32)

    if not opts.watchlistid:
        print "Missing watchlist ID parameter; run with --help for usage"
        sys.exit(-1)

    if opts.watchlistid not in watchlistIds:
        print "Error: Watchlist ID not found"
        sys.exit(-1)

    print
    for watchlist in watchlists:
        if opts.watchlistid == watchlist['id']:
            print "Printing %d results for watchlist: %s" % (opts.numrows, watchlist['name'])
            printWatchlistHits(cb.server, opts.watchlistid, watchlist['index_type'], opts.numrows)
            break


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
