#!/usr/bin/env python

import sys
from cbapi.response.models import Alert
from cbapi.example_helpers import build_cli_parser, get_cb_response_object


def main():
    parser = build_cli_parser()
    parser.add_argument("--query", action="store", default="")

    args = parser.parse_args()

    cb = get_cb_response_object(args)

    alert_query = cb.select(Alert).where(args.query)
    for alert in alert_query:
        if 'binary' in alert.alert_type:
            print("Alert with score {0:d}: Binary {1:s} matched watchlist/report {2:s}".format(alert.report_score,
                                                                                               alert.md5,
                                                                                               alert.watchlist_name))
        else:
            print("Alert with score {0:d}: Process {1:s} matched watchlist/report {2:s}".format(alert.report_score,
                                                                                                alert.process_name,
                                                                                                alert.watchlist_name))
            print("-> visit {0:s} to view this process in the Carbon Black UI.".format(alert.process.webui_link))


if __name__ == "__main__":
    sys.exit(main())