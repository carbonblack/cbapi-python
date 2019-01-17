#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object


def main():
    parser = build_cli_parser("Create a CbTH feed")

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    feed = cb.create_feed(name=args.name, owner=args.owner,
                          provider_url=args.url, summary=args.summary,
                          category=args.category, access=args.access)

    print(feed)


if __name__ == "__main__":
    sys.exit(main())
