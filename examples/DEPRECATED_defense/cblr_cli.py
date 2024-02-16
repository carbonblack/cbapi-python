#!/usr/bin/env python

import sys

import logging

from cbapi.example_helpers import build_cli_parser, get_cb_defense_object, CblrCli
from cbapi.psc.defense import Device

log = logging.getLogger(__name__)


def connect_callback(cb, line):
    try:
        sensor_id = int(line)
    except ValueError:
        sensor_id = None

    if not sensor_id:
        q = cb.select(Device).where("hostNameExact:{0}".format(line))
        sensor = q.first()
    else:
        sensor = cb.select(Device, sensor_id)

    return sensor


def main():
    parser = build_cli_parser("Cb Defense Live Response CLI")
    parser.add_argument("--log", help="Log activity to a file", default='')
    args = parser.parse_args()
    cb = get_cb_defense_object(args)

    if args.log:
        file_handler = logging.FileHandler(args.log)
        file_handler.setLevel(logging.DEBUG)
        log.addHandler(file_handler)

    cli = CblrCli(cb, connect_callback)
    cli.cmdloop()


if __name__ == "__main__":
    sys.exit(main())
