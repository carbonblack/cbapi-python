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
    parser = optparse.OptionParser(usage="%prog [options]", description="Dump Binary Info")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-t", "--installer-type", action="store", default=None, dest="type",
                      help="Installer type; must be one of [WindowsEXE|WindowsMSI]")
    parser.add_option("-f", "--filename", action="store", default=None, dest="filename",
                      help="Filename to save the installer package to")
    parser.add_option("-g", "--sensor-group", action="store", default="1", dest="group",
                      help="Sensor group ID of the group to download an installer for")
    return parser

def truncate(string, length):
    if len(string) + 2 > length:
        return string[:length] + "..."
    return string

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or not opts.type or not opts.group or not opts.filename:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.url, token=opts.token, ssl_verify=opts.ssl_verify)

    # download the installer package 
    #
    print "-> Downloading..."
    bytes = cb.sensor_installer(opts.type, opts.group)
    print "-> Sensor Installer Package is %s bytes" % (len(bytes))
    print "-> Download complete"

    # save the instaler package to disk
    #
    print "-> Saving to %s..." % (opts.filename)
    open(opts.filename, 'wb').write(bytes)
    print "-> Complete"

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
