#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process, Events, Tree, FeedHits
from solrq import Range, Value


def main():
    parser = build_cli_parser("Search processes")
    parser.add_argument("-q", type=str, help="process query", default="process_name:notepad.exe")
    parser.add_argument("-n", type=int, help="only output N proceeses", default=0)
    parser.add_argument("-e", type=bool, help="show events for query results", default=False)
    parser.add_argument("-c", type=bool, help="show children for query results", default=False)

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    print("Number of queries: {}".format(len(cb.queries())))
    print("API limits: {}".format(cb.limits()))

    processes = cb.select(Process).where(args.q)

    print("Number of processes: {}".format(len(processes)))

    for process in processes:
        print(process.process_guid)

        if args.e:
            for event in process.events(event_type=Value("*", safe=True)):
                print(event)

        if args.c:
            for child in process.children():
                print(child)


if __name__ == "__main__":
    sys.exit(main())
