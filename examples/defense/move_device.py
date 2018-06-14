#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_defense_object
from cbapi.psc.defense import Device


def main():
    parser = build_cli_parser("Move a device into a new security policy")
    device_options = parser.add_mutually_exclusive_group(required=True)
    device_options.add_argument("-i", "--id", type=int, help="Device ID of sensor to move")
    device_options.add_argument("-n", "--hostname", help="Hostname to move")

    policy_options = parser.add_mutually_exclusive_group(required=True)
    policy_options.add_argument("--policyid", type=int, help="Policy ID")
    policy_options.add_argument("--policyname", help="Policy name")

    args = parser.parse_args()
    cb = get_cb_defense_object(args)

    if args.id:
        devices = [cb.select(Device, args.id)]
    else:
        devices = list(cb.select(Device).where("hostNameExact:{0}".format(args.hostname)))

    for device in devices:
        if args.policyid:
            destpolicy = int(args.policyid)
            device.policyId = int(args.policyid)
        else:
            destpolicy = args.policyname
            device.policyName = args.policyname

        device.save()
        print("Moved device id {0} (hostname {1}) into policy {2}".format(device.deviceId, device.name, destpolicy))


if __name__ == "__main__":
    sys.exit(main())
