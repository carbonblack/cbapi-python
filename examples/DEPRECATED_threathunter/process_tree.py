#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process


def main():
    parser = build_cli_parser("Query processes")
    parser.add_argument("-p", type=str, help="process guid", default=None)

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    if not args.p:
        print("Error: Missing Process GUID to query the process tree with")
        sys.exit(1)

    tree = cb.select(Process).where(process_guid=args.p)[0].tree()
    for idx, child in enumerate(tree.children):
        print("Child #{}".format(idx))
        print("\tName: {}".format(child.process_name))
        print("\tGUID: {}".format(child.process_guid))
        print("\tNumber of children: {}".format(len(child.children)))


if __name__ == "__main__":
    sys.exit(main())
