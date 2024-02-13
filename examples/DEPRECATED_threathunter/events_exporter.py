#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Event
import json
import csv


def main():
    parser = build_cli_parser("Query processes")
    parser.add_argument("-p", type=str, help="process guid", default=None)
    parser.add_argument("-s", type=bool, help="silent mode", default=False)
    parser.add_argument("-n", type=int, help="only output N events", default=None)
    parser.add_argument("-f", type=str, help="output file name", default=None)
    parser.add_argument("-of", type=str, help="output file format: csv or json", default="json")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    if not args.p:
        print("Error: Missing Process GUID to search for events with")
        sys.exit(1)

    events = cb.select(Event).where(process_guid=args.p)

    if args.n:
        events = events[0:args.n]

    if not args.s:
        for event in events:
            print("Event type: {}".format(event.event_type))
            print("\tEvent GUID: {}".format(event.event_guid))
            print("\tEvent Timestamp: {}".format(event.event_timestamp))

    if args.f is not None:
        if args.of == "json":
            with open(args.f, 'w') as outfile:
                for event in events:
                    json.dump(event.original_document, outfile)
        else:
            with open(args.f, 'w') as outfile:
                csvwriter = csv.writer(outfile)
                for event in events:
                    csvwriter.writerows(event)


if __name__ == "__main__":
    sys.exit(main())
