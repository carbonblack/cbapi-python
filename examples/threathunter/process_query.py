#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Process, Binary
from cbapi.errors import ObjectNotFoundError


def main():
    parser = build_cli_parser("Query processes")
    parser.add_argument("-q", type=str, help="process query", default="process_name:notepad.exe")
    parser.add_argument("-n", type=int, help="only output N processes", default=None)
    parser.add_argument("-b", action="store_true", help="show binary information", default=False)

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    processes = cb.select(Process).where(args.q)

    if args.n:
        processes = processes[0:args.n]

    for process in processes:
        print("Process: {}".format(process.process_name))
        print("\tPIDs: {}".format(process.process_pids))
        print("\tSHA256: {}".format(process.process_sha256))
        print("\tGUID: {}".format(process.process_guid))

        if args.b:
            try:
                binary = cb.select(Binary, process.process_sha256)
                print(binary)
                print(binary.summary)
            except ObjectNotFoundError:
                print("No binary found for process with hash: {}".format(process.process_sha256))


if __name__ == "__main__":
    sys.exit(main())
