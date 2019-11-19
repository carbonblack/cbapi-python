#!/usr/bin/env python
#

import sys
from cbapi.response.models import Sensor
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import logging
import csv
import traceback

log = logging.getLogger(__name__)


def export_sensors(cb, export_file_name, export_fields, query):
    print("Starting CbR Sensor Export")
    if query:
        sensors = list(cb.select(Sensor).where(query).all())
    else:
        sensors = list(cb.select(Sensor))
    with open(export_file_name, "w", encoding="utf8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', lineterminator='\n')
        csv_writer.writerow(export_fields)
        for sensor in sensors:
            try:
                row = [getattr(sensor, field) for field in export_fields]
                csv_writer.writerow(row)
            except Exception as e:
                print("Exception {1} caused sensor export to fail for {0}".format(sensor.hostname, str(e)))
                traceback.format_exc(0)
    print("Export finished, exported {0} sensors to {1}".format(len(sensors), export_file_name))


def main():
    parser = build_cli_parser(description="Export CbR Sensors from your environment as CSV")
    parser.add_argument("--output", "-o", dest="exportfile", help="The file to export to", required=True)
    parser.add_argument("--fields", "-f", dest="exportfields", help="The fields to export",
                        default="id,hostname,group_id,network_interfaces,os_environment_display_string,"
                        "build_version_string,network_isolation_enabled,last_checkin_time",
                        required=False)
    parser.add_argument("--query", "-q", dest="query", help="optional query to filter exported sensors", required=False)
    args = parser.parse_args()
    cb = get_cb_response_object(args)
    export_fields = args.exportfields.split(",")
    return export_sensors(cb, export_file_name=args.exportfile, export_fields=export_fields, query=args.query)


if __name__ == "__main__":
    sys.exit(main())
