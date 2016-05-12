#!/usr/bin/env python

import sys
from cbapi.response.models import Process, Binary
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
from cbapi.errors import ObjectNotFoundError


def main():
    parser = build_cli_parser("Search for cmd.exe writing to exe and dll filepaths")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    for proc in cb.select(Process).where("process_name:cmd.exe (filemod:*.exe or filemod:*.dll)"):
        for fm in proc.filemods:
            if not fm.path.lower().endswith((".exe", ".dll")):
                continue

            signed = ""
            product_name = ""

            if fm.type == "LastWrote" and fm.md5:
                try:
                    b = cb.select(Binary, fm.md5)
                    signed = b.signed
                    product_name = b.product_name
                except ObjectNotFoundError:
                    pass

            print("%s,%s,%s,%s,%s,%s,%s,%s,%s" % (str(fm.timestamp), proc.hostname, proc.username, proc.path,
                                                  fm.path, fm.type, fm.md5, signed, product_name))

if __name__ == "__main__":
    sys.exit(main())
