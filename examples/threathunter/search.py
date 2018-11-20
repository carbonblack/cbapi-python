#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process
from solrq import Q


def main():
    parser = build_cli_parser("Search processes (CbTH)")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    # query = Q(process_name="svchost.exe")
    # query2 = Q(process_name="conhost.exe")
    # processes = cb.select(Process).where(query).or_(query2)
    processes = cb.select(Process).where(process_name="svchost.exe").and_(process_pid=3056)

    for process in processes:
        print(process)


if __name__ == "__main__":
    sys.exit(main())
