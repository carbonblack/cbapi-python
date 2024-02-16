#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object


def main():
    parser = build_cli_parser("Modify a CbTH feed")
    parser.add_argument("--id", type=str, help="Feed ID", default=None)
    parser.add_argument("--name", type=str, help="Feed name", default=None)
    parser.add_argument("--owner", type=str, help="Feed owner", default=None)
    parser.add_argument("--url", type=str, help="Feed provider url", default="https://example.com")
    parser.add_argument("--summary", type=str, help="Feed summary", default=None)
    parser.add_argument("--category", type=str, help="Feed category", default="Partner")
    parser.add_argument("--access", type=str, help="Feed access scope", default="private")

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    feed = cb.feed(args.id)

    print("Before modification:")
    print("=" * 80)
    print(feed)
    print("=" * 80)

    metadata = {}
    if args.name:
        metadata["name"] = args.name
    if args.owner:
        metadata["owner"] = args.owner
    if args.url:
        metadata["provider_url"] = args.url
    if args.summary:
        metadata["summary"] = args.summary
    if args.category:
        metadata["category"] = args.category
    if args.access:
        metadata["access"] = args.access

    feed.feedinfo.update(**metadata)

    print("After modification:")
    print("=" * 80)
    print(feed)
    print("=" * 80)


if __name__ == "__main__":
    sys.exit(main())
