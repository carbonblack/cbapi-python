#!/usr/bin/env python
#

import sys
from cbapi.psc.threathunter.models import Watchlist
from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object
import logging
import json
import time

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

    subscribe_command = commands.add_parser("subscribe", help="Create a watchlist with a feed")
    subscribe_command.add_argument("-i", "--id", type=str, help="The Feed ID", required=True)
    subscribe_command.add_argument("-n", "--name", type=str, help="Watchlist name", required=True)
    subscribe_command.add_argument("-d", "--description", type=str, help="Watchlist description", required=True)
    subscribe_command.add_argument("-t", "--tags", action="store_true", help="Enable tags", default=False)
    subscribe_command.add_argument("-a", "--alerts", action="store_true", help="Enable alerts", default=False)
    subscribe_command.add_argument("-T", "--timestamp", type=int, help="Creation timestamp", default=int(time.time()))
    subscribe_command.add_argument("-U", "--last_update", type=int, help="Last update timestamp", default=int(time.time()))

    create_command = commands.add_parser("create", help="Create a watchlist with a report")
    create_command.add_argument("-n", "--name", type=str, help="Watchlist name", required=True)
    create_command.add_argument("-d", "--description", type=str, help="Watchlist description", required=True)
    create_command.add_argument("-t", "--tags", action="store_true", help="Enable tags", default=False)
    create_command.add_argument("-a", "--alerts", action="store_true", help="Enable alerts", default=False)
    create_command.add_argument("-T", "--timestamp", type=int, help="Creation timestamp", default=int(time.time()))
    create_command.add_argument("-U", "--last_update", type=int, help="Last update timestamp", default=int(time.time()))
    # Report metadata arguments.
    create_command.add_argument("--rep_timestamp", type=int, help="Report timestamp", default=int(time.time()))
    create_command.add_argument("--rep_title", type=str, help="Report title", required=True)
    create_command.add_argument("--rep_desc", type=str, help="Report description", required=True)
    create_command.add_argument("--rep_severity", type=int, help="Report severity", default=1)
    create_command.add_argument("--rep_link", type=str, help="Report link")
    create_command.add_argument("--rep_tags", type=str, help="Report tags, comma separated")
    create_command.add_argument("--rep_visibility", type=str, help="Report visibility")

    alter_report_command = commands.add_parser("alter-report", help="Change the properties of a watchlist's report")
    alter_report_command.add_argument("-i", "--id", type=str, help="Watchlist ID", required=True)
    alter_report_command.add_argument("-r", "--reportid", type=str, help="Report ID", required=True)
    alter_report_command.add_argument("-s", "--severity", type=int, help="The report's severity", required=True)

    alter_ioc_command = commands.add_parser("alter-ioc", help="Change the properties of a watchlist's IOC")

    export_command = commands.add_parser("export", help="Export a watchlist into an importable format")

    import_command = commands.add_parser("import", help="Import a previously exported watchlist")

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
