#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_psc_object
from cbapi.psc import Device


def main():
    parser = build_cli_parser("List devices")
    parser.add_argument("-q", "--query", help="Query string for looking for devices")
    parser.add_argument("-A", "--ad_group_id", action="append", type=int, help="Active Directory Group ID")
    parser.add_argument("-p", "--policy_id", action="append", type=int, help="Policy ID")
    parser.add_argument("-s", "--status", action="append", help="Status of device")
    parser.add_argument("-P", "--priority", action="append", help="Target priority of device")
    parser.add_argument("-S", "--sort_by", help="Field to sort the output by")
    parser.add_argument("-R", "--reverse", action="store_true", help="Reverse order of sort")

    args = parser.parse_args()
    cb = get_cb_psc_object(args)

    query = cb.select(Device)
    if args.query:
        query = query.where(args.query)
    if args.ad_group_id:
        query = query.set_ad_group_ids(args.ad_group_id)
    if args.policy_id:
        query = query.set_policy_ids(args.policy_id)
    if args.status:
        query = query.set_status(args.status)
    if args.priority:
        query = query.set_target_priorities(args.priority)
    if args.sort_by:
        direction = "DESC" if args.reverse else "ASC"
        query = query.sort_by(args.sort_by, direction)

    devices = list(query)
    print("{0:9} {1:40}{2:18}{3}".format("ID", "Hostname", "IP Address", "Last Checkin Time"))
    for device in devices:
        print("{0:9} {1:40s}{2:18s}{3}".format(device.id, device.name or "None",
                                               device.last_internal_ip_address or "Unknown",
                                               device.last_contact_time))


if __name__ == "__main__":
    sys.exit(main())
