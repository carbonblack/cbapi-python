#!/usr/bin/env python

import sys
from cbapi.response.models import Binary
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import shutil


def main():
    parser = build_cli_parser()
    parser.add_argument("--md5", help="binary query", required=True)
    parser.add_argument("--filename", help="local filename to save the binary as", required=True)
    args = parser.parse_args()

    cb = get_cb_response_object(args)
    binary = cb.select(Binary, args.md5)
    shutil.copyfileobj(binary.file, open(args.filename, "wb"))

    print("-> Downloaded binary %s [%u bytes]" % (args.md5, binary.size))

    return 0


if __name__ == "__main__":
    sys.exit(main())
