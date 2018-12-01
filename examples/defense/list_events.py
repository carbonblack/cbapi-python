#!/usr/bin/env python

import sys
import re
from datetime import datetime
from cbapi.defense.models import Event
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object


# converting time to something more readable
def convert_time(epoch_time):
    converted_time = datetime.fromtimestamp(int(epoch_time / 1000.0)).strftime(' %b %d %Y %H:%M:%S')
    return converted_time


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
        #flipped the start and end arguments around so script can be called with the start date being the earliest date.
        #it's just easier on the eyes for most folks

        events = list(cb.select(Event).where("startTime:{0}".format(args.end))) and (
            cb.select(Event).where("endTime:{0}".format(args.start)))
    else:
        events = list(cb.select(Event))


    for event in events:
        # event.refresh()
        #converting times to readable format
        event_time = str(convert_time(event.createTime))
        create_time = str(convert_time(event.eventTime))

        #dicts for parent app, process details, netflow, selected app, and target app.
        netflow = dict(event.netFlow)
        parent_app = dict(event.parentApp)
        target_app = dict(event.targetApp)
        selected_app = dict(event.selectedApp)
        device_details = dict(event.deviceDetails)

        #stripping HTML tags out of the long description
        long_description = strip_html(event.longDescription)
        #format and print out the event time, event ID, Creation time, event type and description
        print("{0:^25}{1:^25}{2:^32}{3}".format("Event Time", "Event ID", "Create Time", "Event Type"))
        print("{0} | {1} | {2} | {3}".format(event_time, event.eventId, create_time, event.eventType))
        print("{0:50}".format("                                    "))
        print("{0} {1}".format("Description: ", long_description))
        print("{0:50}".format("------------------------------------"))
        print("{0:50}".format("                                    "))

        #print out selected app details, target app, parent app details

        print("{0} {1}".format("Selected app: ", selected_app))
        print("{0} {1}".format("Parent app: ", parent_app))
        print("{0} {1}".format("Target app:", target_app))
        print("{0} {1}".format("netflow: ", netflow))
        print("{0:50}".format("                                    "))
        print("{0:50}".format("                                    "))




if __name__ == "__main__":
    sys.exit(main())