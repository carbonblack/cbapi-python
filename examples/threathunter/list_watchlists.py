#!/usr/bin/env python

import sys

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object
from cbapi.psc.threathunter import Watchlist


def main():
    parser = build_cli_parser("List CbTH watchlists")
    # parser.add_argument("-r", help="show the reports in each feed", action="store_true", default=False)

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    watchlists = cb.select(Watchlist)

    for watchlist in watchlists:
        print(watchlist)
        # if args.r:
        #     print("========== reports ==========")
        #     for report in watchlist.reports():
        #         print(report)
        #     print("==========   end   ==========")


if __name__ == "__main__":
    sys.exit(main())
