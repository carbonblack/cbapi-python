#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_psc_object
from cbapi.psc import Device


def toggle_value(args):
    if args.on:
        return True
    if args.off:
        return False
    raise Exception("Unknown toggle value")


def main():
    parser = build_cli_parser("Send control messages to device")
    parser.add_argument("-d", "--device_id", type=int, required=True, help="The ID of the device to be controlled")
    subparsers = parser.add_subparsers(dest="command", help="Device command help")

    bgscan_p = subparsers.add_parser("background_scan", help="Set background scanning status")
    toggle = bgscan_p.add_mutually_exclusive_group(required=True)
    toggle.add_argument("--on", action="store_true", help="Turn background scanning on")
    toggle.add_argument("--off", action="store_true", help="Turn background scanning off")

    bypass_p = subparsers.add_parser("bypass", help="Set bypass mode")
    toggle = bypass_p.add_mutually_exclusive_group(required=True)
    toggle.add_argument("--on", action="store_true", help="Enable bypass mode")
    toggle.add_argument("--off", action="store_true", help="Disable bypass mode")

    subparsers.add_parser("delete", help="Delete sensor")
    subparsers.add_parser("uninstall", help="Uninstall sensor")

    quarantine_p = subparsers.add_parser("quarantine", help="Set quarantine mode")
    toggle = quarantine_p.add_mutually_exclusive_group(required=True)
    toggle.add_argument("--on", action="store_true", help="Enable quarantine mode")
    toggle.add_argument("--off", action="store_true", help="Disable quarantine mode")

    policy_p = subparsers.add_parser("policy", help="Update policy for node")
    policy_p.add_argument("-p", "--policy_id", type=int, required=True, help="New policy ID to set for node")

    sensorv_p = subparsers.add_parser("sensor_version", help="Update sensor version for node")
    sensorv_p.add_argument("-o", "--os", required=True, help="Operating system for sensor")
    sensorv_p.add_argument("-V", "--version", required=True, help="Version number of sensor")

    args = parser.parse_args()
    cb = get_cb_psc_object(args)
    dev = cb.select(Device, args.device_id)

    if args.command:
        if args.command == "background_scan":
            dev.background_scan(toggle_value(args))
        elif args.command == "bypass":
            dev.bypass(toggle_value(args))
        elif args.command == "delete":
            dev.delete_sensor()
        elif args.command == "uninstall":
            dev.uninstall_sensor()
        elif args.command == "quarantine":
            dev.quarantine(toggle_value(args))
        elif args.command == "policy":
            dev.update_policy(args.policy_id)
        elif args.command == "sensor_version":
            dev.update_sensor_version({args.os: args.version})
        else:
            raise NotImplementedError("Unknown command")
        print("OK")
    else:
        print(dev)


if __name__ == "__main__":
    sys.exit(main())
