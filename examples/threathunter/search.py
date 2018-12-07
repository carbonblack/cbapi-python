#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process, Events, Tree, FeedHits
from solrq import Range, Value


def main():
    parser = build_cli_parser("Search processes (CbTH)")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    print("Number of queries: {}".format(len(cb.queries())))
    print("API limits: {}".format(cb.limits()))

    processes = cb.select(Process).where(process_name="notepad.exe")

    print("Number of processes: {}".format(len(processes)))

    process = processes[0]

    events = process.events(event_type=Value("*", safe=True))
    # alternatively:
    # events = cb.select(Events).where(process_guid=process.process_guid)

    print("Number of events: {}".format(len(events)))

    # tree = process.tree()
    # alternatively:
    # tree = cb.select(Tree).where(process_guid=process.process_guid)

    # get the children directly:
    children = process.children()

    print("Number of children: {}".format(len(children)))

    for child in children:
        print(child)


if __name__ == "__main__":
    sys.exit(main())
