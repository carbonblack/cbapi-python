#!/usr/bin/env python

import sys
from cbapi.response.models import Process
from cbapi.example_helpers import build_cli_parser, get_cb_response_object


def main():
    parser = build_cli_parser("Enumerate USB Devices")
    parser.add_argument("--start", "-s", action="store", default=None, dest="start_time",
                        help="Start time (example: -2h)")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    query_string = r'regmod:registry\machine\system\currentcontrolset\control\deviceclasses\{53f56307-b6bf-11d0-94f2-00a0c91efb8b}\*'
    if args.start_time:
        query_string += ' start:{0:s}'.format(args.start_time)

    for proc in cb.select(Process).where(query_string):
        for rm in proc.regmods:
            if "{53f56307-b6bf-11d0-94f2-00a0c91efb8b}" in rm.path:
                pieces = rm.path.split("usbstor#disk&")
                if len(pieces) < 2:
                    print("WARN:::: {0}".format(str(pieces)))
                else:
                    device_info = pieces[1] #.split('{53f56307-b6bf-11d0-94f2-00a0c91efb8b}')[0]
                    print(device_info)


if __name__ == "__main__":
    sys.exit(main())
