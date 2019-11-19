#!/usr/bin/env python

import sys
from cbapi.response.models import Binary
from cbapi.example_helpers import build_cli_parser, get_cb_response_object


def main():
    parser = build_cli_parser()
    parser.add_argument("--filename", help="filename for md5 list", required=True)
    args = parser.parse_args()

    cb = get_cb_response_object(args)
    binary_query = cb.select(Binary).all()

    with open(args.filename, "w") as fp:
        for b in binary_query:
            fp.write("{0:s}\n".format(b.md5sum))

    return 0


if __name__ == "__main__":
    sys.exit(main())
