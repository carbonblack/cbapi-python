#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process


def main():
    parser = build_cli_parser("Search processes")
    parser.add_argument("-q", type=str, help="process query", default="process_name:notepad.exe")
    parser.add_argument("-f", help="show full objects", action="store_true", default=False)
    parser.add_argument("-n", type=int, help="only output N processes", default=None)
    parser.add_argument("-e", help="show events for query results", action="store_true", default=False)
    parser.add_argument("-c", help="show children for query results", action="store_true", default=False)
    parser.add_argument("-p", help="show parents for query results", action="store_true", default=False)
    parser.add_argument("-t", help="show tree for query results", action="store_true", default=False)
    parser.add_argument("-S", type=str, help="sort by this field", required=False)
    parser.add_argument("-D", help="return results in descending order", action="store_true")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    processes = cb.select(Process).where(args.q)

    direction = "ASC"
    if args.D:
        direction = "DESC"

    if args.S:
        processes.sort_by(args.S, direction=direction)

    print("Number of processes: {}".format(len(processes)))

    if args.n:
        processes = processes[0:args.n]

    for process in processes:
        if args.f:
            print(process)
        else:
            print("{} ({}): {}".format(process.process_name, process.process_guid, process.process_sha256))

        if args.e:
            print("=========== events ===========")
            for event in process.events():
                if args.f:
                    print(event)
                else:
                    print("\t{}".format(event.event_type))

        if args.c:
            print("========== children ==========")
            for child in process.children:
                if args.f:
                    print(child)
                else:
                    print("\t{}: {}".format(child.process_name, child.process_sha256))

        if args.p:
            print("========== parents ==========")
            for parent in process.parents:
                if args.f:
                    print(parent)
                else:
                    print("\t{}: {}".format(parent.process_name, parent.process_sha256))

        if args.t:
            print("=========== tree =============")
            tree = process.tree()
            print(tree)
            print(tree.nodes)

        print("===========================")


if __name__ == "__main__":
    sys.exit(main())
