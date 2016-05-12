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
import json
import urllib
import optparse
import cbapi 

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Perform a process search")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-f", "--feed", action="store", default=None, dest="feed",
                      help="feed filename")
    return parser

def search_wrapper(cb, query, index):
    """
    simple search wrapper
    """

    result = {}
    result['Query'] = query

    try:
        if 'events' == index:
            results = cb.process_search(query, rows=0)
        elif 'modules' == index:
            results = cb.binary_search(query, rows=0)
        else:
            raise Exception("Unrecognized index %s" % index)

        result['TotalResults'] = results['total_results']
        result['QTime'] = int(1000*results['elapsed'])
    except Exception, e:
        result['e'] = e

    return result

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or opts.feed is None:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.url, token=opts.token, ssl_verify=opts.ssl_verify)

    # read in the entire feed, decode as JSON, and store
    #
    feed = json.loads(open(opts.feed).read())

    # print a legend
    #
    print "%-20s | %-4s | %-4s | %-7s | %s" % ("report id", "ver", "hits", "QTime", "Query") 
    print "%-20s | %-4s | %-4s | %-7s | %s" % ("-" * 20, "-" * 4, "-" * 4, "-" * 7, "-" * 100)

    # iterate over each report
    #
    for report in feed['reports']:
 
       # ensure report has an iocs element and skip over any reports without a query ioc
       if not report.has_key('iocs') or not report['iocs'].has_key('query'):
            continue    
 
       # ensure report has both an index_type and search_query field 
       q = report['iocs']['query'][0]
       if not q.has_key('index_type') or not q.has_key('search_query'):
           continue

       # ensure that the search_query has a query ("q=") value
       query = None
       urlver = None
       for kvpair in q['search_query'].split('&'):
           if 2 != len(kvpair.split('=')):
               continue

           key = kvpair.split('=')[0]
           val = kvpair.split('=')[1]
           
           if key == 'q':
               query = val
      
           if key == 'cb.urlver':
               urlver = val

       # without a query, nothing to validate
       if query is None:
           continue

       result = search_wrapper(cb, urllib.unquote(query), q['index_type'])
       
       if not result.has_key('e'):
           print "%-20s | %-4s | %-4s | %-7s | %s" % (report.get('id', "<none>"), str(urlver), result.get('TotalResults', 0), str(result.get('QTime', 0)) + "ms", result['Query'])
       else:
           print "ERROR: %s" % result['e']

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
