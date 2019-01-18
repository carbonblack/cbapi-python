#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object


def main():
    parser = build_cli_parser("List CbTH feeds")
    parser.add_argument("-p", help="show public feeds in addition to private ones", action="store_true", default=False)

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    for info in cb.feeds(include_public=args.p):
        print(info)


if __name__ == "__main__":
    sys.exit(main())
