#!/usr/bin/env python
# ZE 2018 AD

import sys
from cbapi.response.models import Alert
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import logging
import traceback

log = logging.getLogger(__name__)

'''
This is a utility designed to use watchlists to perform operations on affected sensors:
supported operations: memory dump, isolation and process termination.
'''


def sensor_operations(cb, watchlists, operation, dryrun=False):
    print("Trying to {0} based on watchlists: {1}".format(operation, watchlists))
    where_clause = " or ".join(("watchlist_name:" + wl for wl in watchlists.split(",")))
    alerts = list(cb.select(Alert).where(where_clause).all())
    for alert in alerts:
        sensor = alert.sensor
        try:
            if not dryrun:
                if operation == "isolate":
                    sensor.isolate()
                elif operation == "memdump":
                    lr = sensor.lr_sesison()
                    lr.memdump("{0}.memdump".format(alert.process.process_guid))
                    lr.close()
                elif operation == "killprocess":
                    lr = sensor.lr_session()
                    lr.kill_process(alert.process.pid)
                    lr.close()
            else:
                print("DRYRUN: would have {0} sensor {1}".format(sensor, operation))
        except Exception:
            print(traceback.format_exc(0))

    print("Sensor operations finished")


def main():
    parser = build_cli_parser(description="Automatic detection and response based on watchlists")
    parser.add_argument("--watchlists", "-w", dest="watchlists", help="The watchlists in question", required=True)
    parser.add_argument("--operation", "-o", dest="operation", help="The operation to perform", required=True,
                        default="Isolate")
    parser.add_argument("--dryrun", "-d", dest="dryrun", help="Dry run mode", default=False, required=False)
    args = parser.parse_args()
    cb = get_cb_response_object(args)
    return sensor_operations(cb, watchlists=args.watchlists, operation=args.operation, dryrun=args.dryrun)


if __name__ == "__main__":
    sys.exit(main())
