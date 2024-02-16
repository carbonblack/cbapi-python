#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_defense_object
from cbapi.psc.defense import Device


def main():
    parser = build_cli_parser("List devices")
    device_options = parser.add_mutually_exclusive_group(required=False)
    device_options.add_argument("-i", "--id", type=int, help="Device ID of sensor")
    device_options.add_argument("-n", "--hostname", help="Hostname")

    args = parser.parse_args()
    cb = get_cb_defense_object(args)

    if args.id:
        devices = [cb.select(Device, args.id)]
    elif args.hostname:
        devices = list(cb.select(Device).where("hostNameExact:{0}".format(args.hostname)))
    else:
        devices = list(cb.select(Device))

    print("{0:9} {1:40}{2:18}{3}".format("ID", "Hostname", "IP Address", "Last Checkin Time"))
    for device in devices:
        print("{0:9} {1:40s}{2:18s}{3}".format(device.deviceId, device.name or "None",
                                               device.lastInternalIpAddress or "Unknown", device.lastContact))


if __name__ == "__main__":
    sys.exit(main())
