#!/usr/bin/env python

from cbapi.response import Process
from collections import defaultdict
from cbapi.six import iteritems
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import sys


class ItemCount(object):
    def __init__(self):
        self.user_counts = defaultdict(int)

    def add(self, username):
        self.user_counts[username.lower()] += 1

    def report(self):
        return sorted(self.user_counts.items(), key=lambda x: x[1], reverse=True)


def main():
    parser = build_cli_parser()
    args = parser.parse_args()
    c = get_cb_response_object(args)

    hostname_user_pairs = defaultdict(ItemCount)
    username_activity = defaultdict(ItemCount)

    for proc in c.select(Process).where("process_name:explorer.exe"):
        hostname_user_pairs[proc.hostname].add(proc.username)
        username_activity[proc.username].add(proc.hostname)

    for hostname, user_activity in iteritems(hostname_user_pairs):
        print("For host {0:s}:".format(hostname))
        for username, count in user_activity.report():
            print("  %-20s: logged in %d times" % (username, count))


if __name__ == '__main__':
    sys.exit(main())
