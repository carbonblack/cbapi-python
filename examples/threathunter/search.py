#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process, Tree


def main():
    parser = build_cli_parser("Search processes (CbTH)")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    # query processes
    processes = cb.select(Process).where(process_name="svchost.exe")

    for process in processes:
        print(process.process_guid)

    # query the process tree
    children = cb.select(Tree).where(process_guid=processes[0].process_guid)

    for child in children:
        print(child)


if __name__ == "__main__":
    sys.exit(main())
