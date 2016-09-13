#!/usr/bin/env python

import sys
from cbapi.response.models import Alert
from cbapi.errors import ApiError
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import time


def main():
    parser = build_cli_parser("Bulk resolve alerts")
    parser.add_argument("--query", action="store", default="",
                        help="The query string of alerts to resolve. All matching alerts will be resolved.")

    args = parser.parse_args()

    cb = get_cb_response_object(args)

    alert_query = cb.select(Alert).where("-status:Resolved " + args.query)
    resolved_alerts = 0
    for alert in alert_query:
        try:
            alert.status = "Resolved"
            alert.save()
        except ApiError as e:
            print("Error resolving {0:s}: {1:s}".format(alert.unique_id, str(e)))
        else:
            resolved_alerts += 1
            print("Resolved {0:s}".format(alert.unique_id))

    if resolved_alerts:
        print("Waiting for alert changes to take effect...")
        time.sleep(25)
        print("Complete. Resolved {0:d} alerts.".format(resolved_alerts))
    else:
        print("Congratulations! You have no unresolved alerts!")


if __name__ == "__main__":
    sys.exit(main())
