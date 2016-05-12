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
    parser = optparse.OptionParser(usage="%prog [options]", description="Perform a binary search")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-q", "--query", action="store", default=None, dest="query",
                      help="binary query")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or opts.query is None:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.url, token=opts.token, ssl_verify=opts.ssl_verify)

    # perform a single binary search
    #
    binaries = cb.binary_search(opts.query)
    
    print "%-20s : %s" % ('Displayed Results', len(binaries['results']))
    print "%-20s : %s" % ('Total Results', binaries['total_results'])
    print "%-20s : %sms" % ('QTime', int(1000*binaries['elapsed']))
    print '\n'

    # for each result 
    for binary in binaries['results']:
        print binary['md5']
        print "-" * 80
        print "%-20s : %s" % ('Size (bytes)', binary.get('orig_mod_len', '<UNKNOWN>'))
        print "%-20s : %s" % ('Signature Status', binary.get('digsig_result', '<UNKNOWN>'))
        print "%-20s : %s" % ('Publisher', binary.get('digsig_publisher', '<UNKNOWN>'))
        print "%-20s : %s" % ('Product Version', binary.get('product_version', '<UNKNOWN>'))
        print "%-20s : %s" % ('File Version', binary.get('file_version', '<UNKNOWN'))
        print "%-20s : %s" % ('64-bit (x64)', binary.get('is_64bit', '<UNKNOWN>'))
        print "%-20s : %s" % ('EXE', binary.get('is_executable_image', '<UNKNOWN>'))
 
        if len(binary.get('observed_filename', [])) > 0:
            print "%-20s : %s" % ('On-Disk Filename(s)', binary['observed_filename'][0].split('\\')[-1])
            for observed_filename in binary['observed_filename'][1:]:
                print "%-20s : %s" % ('', observed_filename.split('\\')[-1])

        print '\n'
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
