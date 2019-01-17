#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object


def main():
    parser = build_cli_parser("Create a CbTH feed")
    parser.add_argument("--name", type=str, help="Feed name", default=None)
    parser.add_argument("--owner", type=str, help="Feed owner", default=None)
    parser.add_argument("--url", type=str, help="Feed provider url", default="https://example.com")
    parser.add_argument("--summary", type=str, help="Feed summary", default=None)
    parser.add_argument("--category", type=str, help="Feed category", default="Partner")
    parser.add_argument("--access", type=str, help="Feed access scope", default="private")

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    feed = cb.create_feed(name=args.name, owner=args.owner,
                          provider_url=args.url, summary=args.summary,
                          category=args.category, access=args.access)

    print(feed)


if __name__ == "__main__":
    sys.exit(main())
