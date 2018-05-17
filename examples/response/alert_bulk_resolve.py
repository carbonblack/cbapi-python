#!/usr/bin/env python

import sys
from cbapi.response.models import Alert
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import time


def main():
    parser = build_cli_parser("Bulk resolve alerts")
    parser.add_argument("--query", action="store", default="", required=True,
                        help="The query string of alerts to resolve. All matching alerts will be resolved.")

    args = parser.parse_args()

    cb = get_cb_response_object(args)

    alert_query = cb.select(Alert).where("-status:Resolved")
    alert_query = alert_query.where(args.query)

    alert_count = len(alert_query)

    if alert_count > 0:
        print("Resolving {0:d} alerts...".format(len(alert_query)))

        alert_query.change_status("Resolved")

        print("Waiting for alert changes to take effect...")
        time.sleep(25)
        print("Complete. Resolved {0:d} alerts.".format(alert_count))
    else:
        print("Congratulations! You have no unresolved alerts!")


if __name__ == "__main__":
    sys.exit(main())
