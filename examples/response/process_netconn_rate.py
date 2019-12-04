#!/usr/bin/env python
#
# The MIT License (MIT)
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
# Usage: process_netconn_rate.py [options]
#
# High avg. netconn/second alert
#
# Options:
#  -h, --help            show this help message and exit
#  -g GT_COUNT, --gt-count=GT_COUNT
#                        Filter processes with greater than [--gt-count]
#                        network events
#  -r CONN_RATE, --rate=CONN_RATE
#                        Alert on processes with more than [--rate] network
#                        connections per second
#  -s, --skip_unknown    Skip processes with unknown start or last update
#
# simple script to detect processes with a high rate of network connections per second
#
#   -Optionally control the minimum total number of connections with the '-g' flag
#       (defaults to > 100)
#   -Optionally control the rate of connections that will generate an alert with the '-r'
#       flag (defaults to > 100 connections/second)
#   -In testing there were some cases that could not identify either a process start time
#       or a process last update time the '-s' flag provide the option to show or hide
#       such processes (defaults to showing those processes)
#
#

import sys
from cbapi.response.models import Process
from cbapi.example_helpers import build_cli_parser, get_cb_response_object


def main():
    parser = build_cli_parser("High avg. netconn/second alert")
    parser.add_argument("--skip-unknown", "-s", action="store_true", default=False, dest="skip_unknown",
                        help="Skip processes with unknown start or last update")
    parser.add_argument("--rate", "-r", type=float, default=100.0, dest="conn_rate",
                        help="Alert on processes with more than [--rate] network connections per second")
    parser.add_argument("--gt-count", "-g", type=int, default=100, dest="gt_count",
                        help="Filter processes with greater than [--gt-count] network events")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    for proc in cb.select(Process).where("netconn_count:[{0:d} TO *]".format(args.gt_count)).sort("last_update desc"):
        try:
            runtime = (proc.last_update - proc.start).total_seconds()
        except Exception:
            if not args.skip_unknown:
                runtime = 1.0
            else:
                continue

        if not runtime and proc.netconn_count > 0:
            # simulate "infinity" so as to avoid a DivideByZero exception
            rate = 1000000
        else:
            rate = proc.netconn_count / float(runtime)

        if rate > args.conn_rate:
            print("{0:s}|{1:s}|{2:s}|{3:.4f}".format(proc.hostname, proc.username, proc.process_name, rate))


if __name__ == "__main__":
    sys.exit(main())
