#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object
import json


def main():
    parser = build_cli_parser("Listen to real-time notifications")
    parser.add_argument("-s", type=int, help="# of seconds to sleep between polls", default=30)

    args = parser.parse_args()
    cb = get_cb_defense_object(args)

    while True:
        for notification in cb.notification_listener(args.s):
            print(json.dumps(notification, indent=2))


if __name__ == "__main__":
    sys.exit(main())
