#!/usr/bin/env python
# Example of using cbapi to get event data
# usage:
# python list_events.py --hostname <hostname> --start<YYYY-MM-DD> --end<YYYY-MM-DD>


# Notes on this script:
#  - script can only pull up to 2 weeks of events at one time ( this is an API limitation)
#  - if no data exists between the start and end range, the script will pull no data.
#  - script can be run with no arguments, it will return events from all endpoints for the past 2 weeks

import sys
import re
from datetime import datetime
from cbapi.psc.defense.models import Event
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object


# Function to format epoch time
def convert_time(epoch_time):
    converted_time = datetime.fromtimestamp(int(epoch_time / 1000.0)).strftime(' %b %d %Y %H:%M:%S')
    return converted_time


# Function to strip HTML from a string.
def strip_html(string):
    p = re.compile(r'<.*?>')
    return p.sub('', string)


def main():
    parser = build_cli_parser("List Events for a device")
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
        # flipped the start and end arguments around so script can be called with the start date being
        # the earliest date. it's just easier on the eyes for most folks.

        events = list(cb.select(Event).where("startTime:{0}".format(args.end))) and (
            cb.select(Event).where("endTime:{0}".format(args.start)))
    else:
        events = list(cb.select(Event))

    for event in events:
        # convert event and create times
        event_time = str(convert_time(event.createTime))
        create_time = str(convert_time(event.eventTime))

        # stripping HTML tags out of the long description
        long_description = strip_html(event.longDescription)

        # format and print out the event time, Event ID, Creation time, Event type and Description
        print("{0:^25}{1:^25}{2:^32}{3}".format("Event Time", "Event ID", "Create Time", "Event Type"))
        print("{0} | {1} | {2} | {3}".format(event_time, event.eventId, create_time, event.eventType))
        print("{0:50}".format("                                    "))
        print("{0} {1}".format("Description: ", long_description))
        print("{0:50}".format("------------------------------------"))
        print("{0:50}".format("                                    "))


if __name__ == "__main__":
    sys.exit(main())
