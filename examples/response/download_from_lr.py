#!/usr/bin/env python
#

import sys
from cbapi.response import Sensor
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import logging

log = logging.getLogger(__name__)


def download_file(sensor, path, output_filename=None):
    with sensor.lr_session() as session:

        # get basename of the file, if output_filename is None
        if output_filename is None:
            if session.os_type == 1:        # Windows uses backslashes
                output_filename = path.split('\\')[-1]
            else:
                output_filename = path.split('/')[-1]

        with open(output_filename, "wb") as fp:
            fp.write(session.get_file(path))
            print("Successfully wrote {0} to local file {1}.".format(path, output_filename))

    return 0


def main():
    parser = build_cli_parser("Download binary from endpoint through Live Response")
    parser.add_argument("-o", "--output", help="Output file name (default is the base file name)")
    parser.add_argument("-H", "--hostname", help="Hostname to download from", required=True)
    parser.add_argument("-p", "--path", help="Path to download", required=True)

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    sensors = cb.select(Sensor).where("hostname:{0}".format(args.hostname))
    for sensor in sensors:
        if sensor.status == "Online":
            return download_file(sensor, args.path, args.output)

    print("No sensors for hostname {0} are online, exiting".format(args.hostname))


if __name__ == "__main__":
    sys.exit(main())
