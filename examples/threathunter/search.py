#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process
from solrq import Q


def main():
    parser = build_cli_parser("Search processes (CbTH)")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    query = Q(process_name="svchost.exe")
    processes = cb.select(Process).where(query)

    for process in processes:
        print(process)


if __name__ == "__main__":
    sys.exit(main())
