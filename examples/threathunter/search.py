#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process, Events, Tree, FeedHits
from solrq import Range, Value


def main():
    parser = build_cli_parser("Search processes")
    parser.add_argument("-q", type=str, help="process query", default="process_name:notepad.exe")
    parser.add_argument("-f", help="show full process objects", action="store_true", default=False)
    parser.add_argument("-n", type=int, help="only output N processes", default=None)
    parser.add_argument("-e", help="show events for query results", action="store_true", default=False)
    parser.add_argument("-c", help="show children for query results", action="store_true", default=False)
    parser.add_argument("-t", help="show tree for query results", action="store_true", default=False)

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    print("Number of queries: {}".format(len(cb.queries())))
    print("API limits: {}".format(cb.limits()))

    processes = cb.select(Process).where(args.q)

    print("Number of processes: {}".format(len(processes)))

    for process in processes[0:args.n]:
        if args.f:
            print(process)
        else:
            print(process.process_guid)

        if args.e:
            print("=========== events ===========")
            for event in process.events(event_type=Value("*", safe=True)):
                print("\t{}".format(event.event_type))

        if args.c:
            print("========== children ==========")
            for child in process.children():
                if args.f:
                    print(child)
                else:
                    print("\t{}: {}".format(child.process_name, child.process_sha256()))

        if args.t:
            print("=========== tree =============")
            tree = process.tree()
            print(tree)
            print(tree.nodes)

        print("===========================")


if __name__ == "__main__":
    sys.exit(main())
