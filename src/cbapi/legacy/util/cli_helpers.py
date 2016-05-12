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
# last updated 2015-03-08 by Ben Johnson bjohnson@bit9.com
#
#

import optparse
import sys
from cbapi import CbApi

def build_cli_parser(description, args):
    """

    :param description:
    :return:
    """
    parser = optparse.OptionParser(usage="%prog [options]", description=description)

    for arg in args:
        parser.add_option(arg[0],
                          arg[1],
                          action=arg[2],
                          default=arg[3],
                          dest=arg[4],
                          help=arg[5])
    return parser



def main_helper(description, main, custom_required=None, custom_optional=None):
    """

    :param description:
    :param main:
    :return:
    """

    default_required = [
                ("-c", "--cburl", "store", None, "server_url",
                 "CB server's URL.  e.g., http://127.0.0.1 "),
                ("-a", "--apitoken", "store", None, "token",
                 "API Token for Carbon Black server")]

    default_optional = [("-n", "--no-ssl-verify", "store_false", True,
                         "ssl_verify", "Do not verify server SSL certificate.")]

    if not custom_required:
        custom_required = []

    if not custom_optional:
        custom_optional = []

    required = default_required + custom_required
    optional = default_optional + custom_optional

    parser = build_cli_parser(description, required + optional)
    opts, args = parser.parse_args()
    for opt in required:
        if not getattr(opts, opt[4]):
            print
            print "** Missing required parameter '%s' **" % opt[4]
            print
            parser.print_help()
            print
            sys.exit(-1)

    args = {}
    for opt in required + optional:
        name = opt[4]
        args[name] = getattr(opts, name)

    cb = CbApi(opts.server_url, ssl_verify=opts.ssl_verify, token=opts.token)
    main(cb, args)
