#!/usr/bin/env python
#

import sys
from cbapi.psc.threathunter.models import Feed
from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object
from cbapi.errors import ServerError
import logging
import json

log = logging.getLogger(__name__)


def list_feeds(cb, parser, args):
    feeds = cb.select(Feed).where(include_public=args.public)

    for feed in feeds:
        print(feed)
        for report in feed.reports():
            print(report)
            for ioc in report.iocs_v2:
                print(ioc)


def list_iocs(cb, parser, args):
    if args.id:
        feed = cb.select(Feed, args.id)
    else:
        feed = [feed for feed in cb.select(Feed) if feed.name == args.feedname]

        if len(feed) > 1:
            print("More than one feed named {}, not continuing".format(args.feedname))
            return

    for report in feed.reports():
        for ioc in report.iocs_v2:
            print(ioc)


def export_feed(cb, parser, args):
    if args.id:
        feed = cb.select(Feed, args.id)
    else:
        feeds = [feed for feed in cb.select(Feed) if feed.name == args.feedname]

        if len(feeds) > 1:
            print("More than one feed named {}, not continuing".format(args.feedname))
            return

        feed = feeds[0]

    for report in feed.reports():
        pass


def import_feed(cb, parser, args):
    json_feed = json.loads(sys.stdin.read())


def delete_feed(cb, parser, args):
    if args.id:
        feed = cb.select(Feed, args.id)
    else:
        feeds = [feed for feed in cb.select(Feed) if feed.name == args.feedname]

        if len(feeds) > 1:
            print("More than one feed named {}, not continuing".format(args.feedname))
            return

        feed = feeds[0]

    feed.delete()


def export_report(cb, parser, args):
    pass


def import_report(cb, parser, args):
    pass


def delete_report(cb, parser, args):
    pass


def replace_report(cb, parser, args):
    pass


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="Feed commands", dest="command_name")

    list_command = commands.add_parser("list", help="List all configured feeds")
    list_command.add_argument("-P", "--public", help="Include public feeds", action="store_true", default=False)

    list_iocs_command = commands.add_parser("list-iocs", help="List all IOCs for a feed")
    specifier = list_iocs_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    export_command = commands.add_parser("export", help="Export a feed into an importable format")
    specifier = export_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    import_command = commands.add_parser("import", help="Import a previously exported feed")

    del_command = commands.add_parser("delete", help="Delete feed")
    specifier = del_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    export_report_command = commands.add_parser("export-report", help="Export a feed's report into an importable format")

    import_report_command = commands.add_parser("import-report", help="Import a previously exported report")

    delete_report_command = commands.add_parser("delete-report", help="Delete a report from a feed")

    replace_report_command = commands.add_parser("replace-report", help="Replace a feed's report")

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    if args.command_name == "list":
        return list_feeds(cb, parser, args)
    elif args.command_name == "list-iocs":
        return list_iocs(cb, parser, args)
    elif args.command_name == "export":
        return export_feed(cb, parser, args)
    elif args.command_name == "import":
        return import_feed(cb, parser, args)
    elif args.command_name == "delete":
        return delete_feed(cb, parser, args)
    elif args.command_name == "export-report":
        return export_report(cb, parser, args)
    elif args.command_name == "import-report":
        return import_report(cb, parser, args)
    elif args.command_name == "delete-report":
        return delete_report(cb, parser, args)
    elif args.command_name == "replace-report":
        return replace_report(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
