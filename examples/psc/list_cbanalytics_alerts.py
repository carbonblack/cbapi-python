#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_psc_object
from cbapi.psc.models import CBAnalyticsAlert
from helpers.alertsv6 import setup_parser_with_cbanalytics_criteria, load_cbanalytics_criteria


def main():
    parser = build_cli_parser("List CB Analytics alerts")
    setup_parser_with_cbanalytics_criteria(parser)
    parser.add_argument("-S", "--sort_by", help="Field to sort the output by")
    parser.add_argument("-R", "--reverse", action="store_true", help="Reverse order of sort")

    args = parser.parse_args()
    cb = get_cb_psc_object(args)

    query = cb.select(CBAnalyticsAlert)
    load_cbanalytics_criteria(query, args)
    if args.sort_by:
        direction = "DESC" if args.reverse else "ASC"
        query = query.sort_by(args.sort_by, direction)

    alerts = list(query)
    print("{0:40} {1:40s} {2:40s} {3}".format("ID", "Hostname", "Threat ID", "Last Updated"))
    for alert in alerts:
        print("{0:40} {1:40s} {2:40s} {3}".format(alert.id, alert.device_name or "None",
                                                  alert.threat_id or "Unknown",
                                                  alert.last_update_time))


if __name__ == "__main__":
    sys.exit(main())
