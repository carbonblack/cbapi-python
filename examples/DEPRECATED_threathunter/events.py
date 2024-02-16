#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Event


def main():
    parser = build_cli_parser("Query processes")
    parser.add_argument("-p", type=str, help="process guid", default=None)
    parser.add_argument("-n", type=int, help="only output N events", default=None)

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    if not args.p:
        print("Error: Missing Process GUID to search for events with")
        sys.exit(1)

    events = cb.select(Event).where(process_guid=args.p)

    if args.n:
        events = events[0:args.n]

    for event in events:
        print("Event type: {}".format(event.event_type))
        print("\tEvent GUID: {}".format(event.event_guid))
        print("\tEvent Timestamp: {}".format(event.event_timestamp))


if __name__ == "__main__":
    sys.exit(main())
