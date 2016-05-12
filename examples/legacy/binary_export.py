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
    parser = optparse.OptionParser(usage="%prog [options]", description="Dump All MD5s from the binary index")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-p", "--pagesize", action="store", default=128, dest="pagesize",
                      help="Number of MD5s to retrieve during each API invocation")
    parser.add_option("-f", "--file", action="store", default=None, dest="filename",
                      help="filename of file to write all md5s to")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or not opts.pagesize or not opts.filename:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.url, token=opts.token, ssl_verify=opts.ssl_verify)

    start = 0
    md5s = []
    total = 0

    while True:
   
        # perform a single binary search
        #
        binaries = cb.binary_search("", rows=int(opts.pagesize), start=start)
        
        if 0 == start:
            total = int(binaries['total_results'])
            print "Total MD5 count is %s" % (binaries['total_results'])

        # api indicates "no more" by returning an empty result set
        #
        if 0 == len(binaries['results']):
            break

        # for each result 
        for binary in binaries['results']:
            md5s.append(binary['md5'])
 
        print '%s of %s complete (%s%%)' % (len(md5s), total, (100 * len(md5s)) / total)

        start = start + int(opts.pagesize)

    f = open(opts.filename, 'w')
    for md5 in md5s:
        f.write("%s\n" % (md5,))
    f.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
