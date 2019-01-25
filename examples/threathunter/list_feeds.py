#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object
from cbapi.psc.threathunter import Feed


def main():
    parser = build_cli_parser("List CbTH feeds")
    parser.add_argument("-p", help="show public feeds in addition to private ones", action="store_true", default=False)
    parser.add_argument("-r", help="show the reports in each feed", action="store_true", default=False)

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    feeds = cb.select(Feed).where(include_public=args.p)

    for feed in feeds:
        print(feed)
        if args.r:
            print("========== reports ==========")
            for report in feed.reports():
                print(report)
            print("==========   end   ==========")

if __name__ == "__main__":
    sys.exit(main())
