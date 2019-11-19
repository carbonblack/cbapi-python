#!/usr/bin/env python
#

import sys
from cbapi.psc.threathunter.models import Watchlist, Report, Feed
from cbapi.example_helpers import eprint, read_iocs, build_cli_parser, get_cb_threathunter_object
from cbapi.errors import ObjectNotFoundError
import logging
import json
import time
import hashlib

log = logging.getLogger(__name__)


def get_watchlist(cb, watchlist_id=None, watchlist_name=None):
    if watchlist_id:
        return cb.select(Watchlist, watchlist_id)
    elif watchlist_name:
        feeds = [feed for feed in cb.select(Watchlist) if feed.name == watchlist_name]

        if not feeds:
            eprint("No watchlist named {}".format(watchlist_name))
            sys.exit(1)
        elif len(feeds) > 1:
            eprint("More than one feed named {}, not continuing".format(watchlist_name))
            sys.exit(1)

        return feeds[0]
    else:
        raise ValueError("expected either watchlist_id or watchlist_name")


def get_report(watchlist, report_id=None, report_name=None):
    if report_id:
        reports = [report for report in watchlist.reports if report.id == report_id]
    elif report_name:
        reports = [report for report in watchlist.reports if report.title == report_name]
    else:
        raise ValueError("expected either report_id or report_name")

    if not reports:
        eprint("No matching reports found.")
        sys.exit(1)
    if len(reports) > 1:
        eprint("More than one matching report found.")
        sys.exit(1)

    return reports[0]


def get_report_feed(watchlist, report_id=None, report_name=None):
    reports = watchlist.feed.reports

    if report_id:
        reports = [report for report in reports if report.id == report_id]
    elif report_name:
        reports = [report for report in reports if report.title == report_name]
    else:
        raise ValueError("expected either report_id or report_name")

    if not reports:
        eprint("No matching reports found.")
        sys.exit(1)
    if len(reports) > 1:
        eprint("More than one matching report found.")
        sys.exit(1)

    return reports[0]


def list_watchlists(cb, parser, args):
    watchlists = cb.select(Watchlist)

    for watchlist in watchlists:
        print(watchlist)
        if args.reports:
            for report in watchlist.reports:
                print(report)
            if watchlist.feed:
                for report in watchlist.feed.reports:
                    print(report)


def subscribe_watchlist(cb, parser, args):
    try:
        cb.select(Feed, args.feed_id)
    except ObjectNotFoundError:
        eprint("Nonexistent or private feed: {}".format(args.feed_id))
        sys.exit(1)

    classifier = {
        "key": "feed_id",
        "value": args.feed_id,
    }

    watchlist_dict = {
        "name": args.watchlist_name,
        "description": args.description,
        "tags_enabled": args.tags,
        "alerts_enabled": args.alerts,
        "create_timestamp": args.timestamp,
        "last_update_timestamp": args.last_update,
        "report_ids": [],
        "classifier": classifier,
    }

    watchlist = cb.create(Watchlist, watchlist_dict)
    watchlist.save()


def create_watchlist(cb, parser, args):
    watchlist_dict = {
        "name": args.watchlist_name,
        "description": args.description,
        "tags_enabled": args.tags,
        "alerts_enabled": args.alerts,
        "create_timestamp": args.timestamp,
        "last_update_timestamp": args.last_update,
        "report_ids": [],
        "classifier": None,
    }

    rep_tags = []
    if args.rep_tags:
        rep_tags = args.rep_tags.split(",")

    report_dict = {
        "timestamp": args.rep_timestamp,
        "title": args.rep_title,
        "description": args.rep_desc,
        "severity": args.rep_severity,
        "link": args.rep_link,
        "tags": rep_tags,
        "iocs_v2": [],  # NOTE(ww): The feed server will convert IOCs to v2s for us.
    }

    report_id, iocs = read_iocs(cb)

    report_dict["id"] = report_id
    report_dict["iocs"] = iocs

    report = cb.create(Report, report_dict)
    report.save_watchlist()

    watchlist_dict["report_ids"].append(report.id)
    watchlist = cb.create(Watchlist, watchlist_dict)
    watchlist.save()


def delete_watchlist(cb, parser, args):
    watchlist = get_watchlist(cb, watchlist_id=args.watchlist_id, watchlist_name=args.watchlist_name)

    if args.reports:
        [report.delete() for report in watchlist.reports]

    watchlist.delete()


def alter_report(cb, parser, args):
    watchlist = get_watchlist(cb, watchlist_id=args.watchlist_id)

    if watchlist.reports:
        report = get_report(watchlist, report_id=args.report_id)
    else:
        report = get_report_feed(watchlist, report_id=args.report_id)

    if args.severity:
        if watchlist.reports:
            report.update(severity=args.severity)
        else:
            report.custom_severity = args.severity

    if args.activate:
        report.unignore()
    elif args.deactivate:
        report.ignore()


def alter_ioc(cb, parser, args):
    watchlist = get_watchlist(cb, watchlist_id=args.watchlist_id)
    report = get_report(watchlist, report_id=args.report_id)

    iocs = [ioc for ioc in report.iocs_ if ioc.id == args.ioc_id]

    if not iocs:
        eprint("No IOC with ID {} found.".format(args.ioc_id))
        sys.exit(1)
    elif len(iocs) > 1:
        eprint("More than one IOC with ID {} found.".format(args.ioc_id))
        sys.exit(1)

    if args.activate:
        iocs[0].unignore()
    elif args.deactivate:
        iocs[0].ignore()


def export_watchlist(cb, parser, args):
    watchlist = get_watchlist(cb, watchlist_id=args.watchlist_id, watchlist_name=args.watchlist_name)
    exported = {
        'watchlist': watchlist._info,
    }

    exported['reports'] = [report._info for report in watchlist.reports]

    print(json.dumps(exported))


def import_watchlist(cb, parser, args):
    imported = json.loads(sys.stdin.read())

    # clear any report IDs, since we'll regenerate them
    imported["watchlist"]["report_ids"].clear()

    watchlist = cb.create(Watchlist, imported['watchlist'])
    watchlist.save()

    # import each report and extract its new ID
    report_ids = []
    for rep_dict in imported["reports"]:

        # NOTE(ww): Previous versions of the CbTH Watchlist API weren't
        # generating IOC IDs on the server side. If they don't show up
        # in our import, generate them manually.
        for ioc in rep_dict["iocs_v2"]:
            if not ioc["id"]:
                ioc_id = hashlib.md5()
                ioc_id.update(str(time.time()).encode("utf-8"))
                [ioc_id.update(value.encode("utf-8")) for value in ioc["values"]]
                ioc["id"] = ioc_id.hexdigest()
        report = cb.create(Report, rep_dict)
        report.save_watchlist()
        report_ids.append(report.id)

    # finally, update our new watchlist with the imported reports
    if report_ids:
        watchlist.update(report_ids=report_ids)


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="Feed commands", dest="command_name")

    list_command = commands.add_parser("list", help="List all configured watchlists")
    list_command.add_argument("-r", "--reports", action="store_true", help="List reports for each watchlist",
                              default=False)

    subscribe_command = commands.add_parser("subscribe", help="Create a watchlist with a feed")
    subscribe_command.add_argument("-i", "--feed_id", type=str, help="The Feed ID", required=True)
    subscribe_command.add_argument("-w", "--watchlist_name", type=str, help="Watchlist name", required=True)
    subscribe_command.add_argument("-d", "--description", type=str, help="Watchlist description", required=True)
    subscribe_command.add_argument("-t", "--tags", action="store_true", help="Enable tags", default=False)
    subscribe_command.add_argument("-a", "--alerts", action="store_true", help="Enable alerts", default=False)
    subscribe_command.add_argument("-T", "--timestamp", type=int, help="Creation timestamp", default=int(time.time()))
    subscribe_command.add_argument("-U", "--last_update", type=int, help="Last update timestamp",
                                   default=int(time.time()))

    create_command = commands.add_parser("create", help="Create a watchlist with a report")
    create_command.add_argument("-w", "--watchlist_name", type=str, help="Watchlist name", required=True)
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

    delete_command = commands.add_parser("delete", help="Delete a watchlist")
    delete_command.add_argument("-R", "--reports", action="store_true", help="Delete all associated reports too",
                                default=False)
    specifier = delete_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--watchlist_id", type=str, help="The watchlist ID")
    specifier.add_argument("-w", "--watchlist_name", type=str, help="The watchlist name")

    alter_report_command = commands.add_parser("alter-report", help="Change the properties of a watchlist's report")
    alter_report_command.add_argument("-i", "--watchlist_id", type=str, help="Watchlist ID", required=True)
    alter_report_command.add_argument("-r", "--report_id", type=str, help="Report ID", required=True)
    alter_report_command.add_argument("-s", "--severity", type=int, help="The report's severity", required=False)
    specifier = alter_report_command.add_mutually_exclusive_group(required=False)
    specifier.add_argument("-d", "--deactivate", action="store_true", help="Deactive alerts for this report")
    specifier.add_argument("-a", "--activate", action="store_true", help="Activate alerts for this report")

    alter_ioc_command = commands.add_parser("alter-ioc", help="Change the properties of a watchlist's IOC")
    alter_ioc_command.add_argument("-i", "--watchlist_id", type=str, help="Watchlist ID", required=True)
    alter_ioc_command.add_argument("-r", "--report_id", type=str, help="Report ID", required=True)
    alter_ioc_command.add_argument("-I", "--ioc_id", type=str, help="IOC ID", required=True)
    specifier = alter_ioc_command.add_mutually_exclusive_group(required=False)
    specifier.add_argument("-d", "--deactivate", action="store_true", help="Deactive alerts for this IOC")
    specifier.add_argument("-a", "--activate", action="store_true", help="Activate alerts for this IOC")

    export_command = commands.add_parser("export", help="Export a watchlist into an importable format")
    specifier = export_command.add_mutually_exclusive_group(required=True)
    specifier.add_argument("-i", "--watchlist_id", type=str, help="Watchlist ID")
    specifier.add_argument("-w", "--watchlist_name", type=str, help="Watchlist name")

    commands.add_parser("import", help="Import a previously exported watchlist")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    if args.command_name == "list":
        return list_watchlists(cb, parser, args)
    elif args.command_name == "subscribe":
        return subscribe_watchlist(cb, parser, args)
    elif args.command_name == "create":
        return create_watchlist(cb, parser, args)
    elif args.command_name == "delete":
        return delete_watchlist(cb, parser, args)
    elif args.command_name == "alter-report":
        return alter_report(cb, parser, args)
    elif args.command_name == "alter-ioc":
        return alter_ioc(cb, parser, args)
    elif args.command_name == "export":
        return export_watchlist(cb, parser, args)
    elif args.command_name == "import":
        return import_watchlist(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
