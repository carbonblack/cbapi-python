#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Event
import json
import csv 


def main(): 
    parser = build_cli_parser("Query processes")
    parser.add_argument("-p", type=str, help="process guid", default=None)
    parser.add_argument("-q",type=str,help="query string",default=None)
    parser.add_arguement("-s",type=bool, help="silent mode",default=False)
    parser.add_argument("-n", type=int, help="only output N events", default=None)
    parser.add_argument("-f", type=str, help="output file name",default=None)
    parser.add_argument("-of", type=str,help="output file format: csv or json",default="json")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    if not args.p and not args.q:
        print("Error: Missing Process GUID to search for events with")
        sys.exit(1)

    if args.q:
        events = cb.select(Event).where(args.q)
    else:
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
                    json.dump(events, outfile)
        else:
            with open(args.f, 'w') as outfile:
                csvwriter = csv.writer(outfile)
                csvwriter.writerows(events)


if __name__ == "__main__":
    sys.exit(main())
