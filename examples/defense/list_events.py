#!/usr/bin/env python

import sys
from cbapi.defense.models import Event
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object


def main():
    parser = build_cli_parser("List events")
    event_options = parser.add_mutually_exclusive_group(required=False)
    event_date_options = parser.add_argument_group("Date Range Arguments")
    event_date_options.add_argument("--start", help="start time")
    event_date_options.add_argument("--end", help="end time")
    event_options.add_argument("-n", "--hostname", help="Hostname")

    args = parser.parse_args()
    cb = get_cb_defense_object(args)

    if args.hostname:
        events = list(cb.select(Event).where("hostNameExact:{0}".format(args.hostname)))
    elif args.start and args.end:
        events = list(cb.select(Event).where("startTime:{0}".format(args.start))) and (
            cb.select(Event).where("endTime:{0}".format(args.end)))
    else:
        events = list(cb.select(Event))

    for event in events:
        #you can print what you want to see here the event object is just being printed as an example

        print(event.alertCategory)
        print(event.alertScore)
        print(event.attackStage)


if __name__ == "__main__":
    sys.exit(main())