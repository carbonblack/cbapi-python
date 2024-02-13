#!/usr/bin/env python
#

import sys
from cbapi.psc.threathunter.models import Feed, Report
from cbapi.example_helpers import eprint, build_cli_parser, get_cb_threathunter_object
import logging
import json

log = logging.getLogger(__name__)


def get_feed(cb, feed_id=None, feed_name=None):
    if feed_id:
        return cb.select(Feed, feed_id)
    elif feed_name:
        feeds = [feed for feed in cb.select(Feed) if feed.name == feed_name]

        if not feeds:
            eprint("No feeds named '{}'".format(feed_name))
            sys.exit(1)
        elif len(feeds) > 1:
            eprint("More than one feed named '{}'".format(feed_name))
            sys.exit(1)

        return feeds[0]
    else:
        raise ValueError("expected either feed_id or feed_name")


def get_report(feed, report_id=None, report_name=None):
    if report_id:
        reports = [report for report in feed.reports if report.id == report_id]

        if not reports:
            eprint("No reports with ID '{}'".format(report_id))
            sys.exit(1)
        elif len(reports) > 1:
            eprint("More than one report with ID '{}'".format(report_id))
            sys.exit(1)
    elif report_name:
        reports = [report for report in feed.reports if report.title == report_name]

        if not reports:
            eprint("No reports named '{}'".format(report_name))
            sys.exit(1)
        elif len(reports) > 1:
            eprint("More than one report named '{}'".format(report_name))
            sys.exit(1)
    else:
        raise ValueError("expected either report_id or report_name")

    return reports[0]


def list_feeds(cb, parser, args):
    if args.iocs and not args.reports:
        eprint("--iocs specified without --reports")
        sys.exit(1)

    feeds = cb.select(Feed).where(include_public=args.public)

    for feed in feeds:
        print(feed)
        if args.reports:
            for report in feed.reports:
                print(report)
                if args.iocs:
                    for ioc in report.iocs_:
                        print(ioc)


def list_iocs(cb, parser, args):
    feed = get_feed(cb, feed_id=args.id, feed_name=args.feedname)

    for report in feed.reports:
        for ioc in report.iocs_:
            print(ioc)


def export_feed(cb, parser, args):
    feed = get_feed(cb, feed_id=args.id, feed_name=args.feedname)

    exported = {}

    exported["feedinfo"] = feed._info
    exported["reports"] = [report._info for report in feed.reports]
    print(json.dumps(exported))


def import_feed(cb, parser, args):
    imported = json.loads(sys.stdin.read())

    if args.feedname:
        imported["feedinfo"]["name"] = args.feedname

    feed = cb.create(Feed, imported)
    feed.save(public=args.public)


def delete_feed(cb, parser, args):
    feed = get_feed(cb, feed_id=args.id, feed_name=args.feedname)
    feed.delete()


def export_report(cb, parser, args):
    feed = get_feed(cb, feed_id=args.id, feed_name=args.feedname)
    report = get_report(feed, report_id=args.reportid, report_name=args.reportname)

    print(json.dumps(report._info))


def import_report(cb, parser, args):
    feed = get_feed(cb, feed_id=args.id, feed_name=args.feedname)

    imp_dict = json.loads(sys.stdin.read())

    reports = feed.reports
    existing_report = next(
        (report for report in reports if imp_dict["id"] == report.id), None
    )

    if existing_report:
        eprint("Report already exists; use replace-report.")
        sys.exit(1)
    else:
        imp_report = cb.create(Report, imp_dict)
        feed.append_reports([imp_report])


def delete_report(cb, parser, args):
    feed = get_feed(cb, feed_id=args.id, feed_name=args.feedname)
    report = get_report(feed, report_id=args.reportid, report_name=args.reportname)
    report.delete()


def replace_report(cb, parser, args):
    feed = get_feed(cb, feed_id=args.id, feed_name=args.feedname)

    imported = json.loads(sys.stdin.read())

    reports = feed.reports
    existing_report = next(
        (report for report in reports if imported["id"] == report.id), None
    )

    if existing_report:
        existing_report.update(**imported)
    else:
        eprint("No existing report to replace")
        sys.exit(1)


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="Feed commands", dest="command_name")

    list_command = commands.add_parser("list", help="List all configured feeds")
    list_command.add_argument(
        "-P",
        "--public",
        help="Include public feeds",
        action="store_true",
        default=False,
    )
    list_command.add_argument(
        "-r",
        "--reports",
        help="Include reports for each feed",
        action="store_true",
        default=False,
    )
    list_command.add_argument(
        "-i",
        "--iocs",
        help="Include IOCs for each feed's reports",
        action="store_true",
        default=False,
    )

    list_iocs_command = commands.add_parser(
        "list-iocs", help="List all IOCs for a feed"
    )
    specifier = list_iocs_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    export_command = commands.add_parser(
        "export", help="Export a feed into an importable format"
    )
    specifier = export_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    import_command = commands.add_parser(
        "import", help="Import a previously exported feed"
    )
    import_command.add_argument(
        "-f", "--feedname", type=str, help="Renames the imported feed"
    )
    import_command.add_argument(
        "-P", "--public", help="Make the feed public", action="store_true"
    )

    del_command = commands.add_parser("delete", help="Delete feed")
    specifier = del_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    export_report_command = commands.add_parser(
        "export-report", help="Export a feed's report into an importable format"
    )
    specifier = export_report_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")
    specifier = export_report_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-I", "--reportid", type=str, help="Report ID")
    specifier.add_argument("-r", "--reportname", type=str, help="Report Name")

    import_report_command = commands.add_parser(
        "import-report", help="Import a previously exported report"
    )
    specifier = import_report_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    delete_report_command = commands.add_parser(
        "delete-report", help="Delete a report from a feed"
    )
    specifier = delete_report_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")
    specifier = delete_report_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-I", "--reportid", type=str, help="Report ID")
    specifier.add_argument("-r", "--reportname", type=str, help="Report Name")

    replace_report_command = commands.add_parser(
        "replace-report", help="Replace a feed's report"
    )
    specifier = replace_report_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--id", type=str, help="Feed ID")
    specifier.add_argument("-f", "--feedname", type=str, help="Feed Name")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

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
