#!/usr/bin/env python
#

import sys
from cbapi.psc.threathunter.models import Watchlist
from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object
import logging
import json

log = logging.getLogger(__name__)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_watchlist(cb, watchlist_id=None, watchlist_name=None):
    if watchlist_id:
        return cb.select(Watchlist, watchlist_id)
    elif watchlist_name:
        feeds = [feed for feed in cb.select(Watchlist) if feed.name == watchlist_name]

        if len(feeds) > 1:
            eprint("More than one feed named {}, not continuing".format(watchlist_name))
            sys.exit(1)

        return feeds[0]
    else:
        raise ValueError("expected either watchlist_id or watchlist_name")


def list_watchlists(cb, parser, args):
    watchlists = cb.select(Watchlist)

    for watchlist in watchlists:
        print(watchlist)


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="Feed commands", dest="command_name")

    commands.add_parser("list", help="List all configured feeds")

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    if args.command_name == "list":
        return list_watchlists(cb, parser, args)
    elif args.command_name == "subscribe":
        pass
    elif args.command_name == "create":
        pass
    elif args.command_name == "alter-report":
        pass
    elif args.command_name == "alter-ioc":
        pass
    elif args.command_name == "export":
        pass
    elif args.command_name == "import":
        pass


if __name__ == "__main__":
    sys.exit(main())
