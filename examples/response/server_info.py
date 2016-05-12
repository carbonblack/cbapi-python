#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_response_object


def output_info(server, info):
    print(server)
    print("-" * 80)
    for key in sorted(info.keys()):
        print("%-30s : %s" % (key, info[key]))


def main():
    parser = build_cli_parser()
    args = parser.parse_args()
    cb = get_cb_response_object(args)

    output_info(cb.url, cb.info())


if __name__ == "__main__":
    sys.exit(main())
