#!/usr/bin/env python
#

import sys
from cbapi.response.models import Process
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
from cbapi.errors import ObjectNotFoundError
import logging

log = logging.getLogger(__name__)


class CountChildren(object):
    def __init__(self):
        self.count = 0

    def walk(self, proc, depth):
        self.count += 1


class ChildCmdlines(object):
    def __init__(self):
        self.cmdlines = []

    def walk(self, proc, depth):
        self.cmdlines.append(proc.cmdline)


def count_children(proc):
    child_counter = CountChildren()
    try:
        proc.walk_children(child_counter.walk)
    except ObjectNotFoundError:
        pass
    return [child_counter.count]


def child_cmdlines(proc):
    cmdlines = ChildCmdlines()
    try:
        proc.walk_children(cmdlines.walk)
    except ObjectNotFoundError:
        pass
    return cmdlines.cmdlines


def process_hit(cb, parent_proc_name, proc_name, value, ratio, child_behavior):
    rows = []
    q = "parent_name:{0} process_name:{1}".format(parent_proc_name, proc_name)
    for child_proc in cb.select(Process).where(q):
        row = []
        row.append(parent_proc_name)
        row.append(proc_name)
        row.append(value)
        row.append(ratio)
        row.append(q)
        row.append(child_proc.hostname)
        row.append(child_proc.username)
        row.append(child_proc.webui_link)
        row.append(child_proc.cmdline)

        row.extend(child_behavior(child_proc))

        rows.append(row)
    return rows


def main():
    parser = build_cli_parser("Term Frequency Analysis")
    parser.add_argument("-p", "--percentage", action="store", default="2", dest="percentless",
                        help="Max Percentage of Term Frequency e.g., 2 ")

    process_selection = parser.add_mutually_exclusive_group(required=True)
    process_selection.add_argument("-t", "--term", action="store", default=None, dest="procname",
                                   help="Comma separated list of parent processes to get term frequency")
    process_selection.add_argument("-f", "--termfile", action="store", default=None, dest="procnamefile",
                                   help="Text file new line separated list of parent processes to get term frequency")

    output_selection = parser.add_mutually_exclusive_group(required=False)
    output_selection.add_argument("--count", action="store_true",
                                  help="Count the child processes that match [default]")
    output_selection.add_argument("--cmdline", action="store_true",
                                  help="Output list of child process command lines")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    if args.procnamefile:
        processes = [s.strip() for s in open(args.procnamefile).readlines()]
    else:
        processes = [s.strip() for s in args.procname.split(",")]

    behavior = count_children
    if args.cmdline:
        behavior = child_cmdlines

    rows = []
    for parent_proc in processes:
        process_facets = cb.select(Process).where("parent_name:{0}".format(parent_proc)).facets("process_name")
        for term in reversed(process_facets["process_name"]):
            termratio = int(float(term['ratio']))
            if int(args.percentless) >= termratio:
                rows.extend(process_hit(cb, parent_proc, term["name"], term["value"], term["ratio"], behavior))

    for row in rows:
        print(",".join([str(x) for x in row]))


if __name__ == "__main__":
    sys.exit(main())
