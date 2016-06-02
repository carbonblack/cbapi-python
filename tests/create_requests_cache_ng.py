#!/usr/bin/env python
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Carbon Black Inc.
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
#  last updated 2016-04-07 by Jason McFarland
#
import sys
import os
import requests_cache

import optparse

from cbapi.response.models import Process, Binary, Sensor, Feed, Watchlist, Investigation, User
from cbapi.response.rest_api import CbEnterpriseResponseAPI

import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


def large_process_search():
    processes = cb.select(Process).where('')
    print "Number of process: ", len(processes)


def large_binary_search():
    binaries = cb.select(Binary).where('')
    print "Number of binaries: ", len(binaries)


def sensor_search():
    sensors = cb.select(Sensor)
    print "Number of sensors: ", len(sensors)


def watchlist_search():
    watchlists = cb.select(Watchlist)
    print "Number of watchlists: ", len(watchlists)


def feed_search():
    feeds = cb.select(Feed)
    print "Number of feeds: ", len(feeds)


def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.cache_name:
        parser.print_help()
        sys.exit(-1)

    global cache_file_name
    cache_file_name = opts.cache_name
    requests_cache.install_cache(cache_file_name, allowable_methods=('GET', 'POST'))

    global cb
    cb = CbEnterpriseResponseAPI()

    large_process_search()
    large_binary_search()
    sensor_search()
    watchlist_search()
    feed_search()


def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]",
                                   description="Create a cache of responses for regression testing")

    #
    # for each supported output type, add an option
    #
    parser.add_option("-f", "--cache", action="store", default="cache", dest="cache_name",
                      help="Cache sqlite file name")
    return parser


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))