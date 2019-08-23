#!/usr/bin/env python

import sys
import time

from cbapi.example_helpers import read_iocs, build_cli_parser, get_cb_threathunter_object
from cbapi.psc.threathunter import Feed


def main():
    parser = build_cli_parser("Create a CbTH feed and, optionally, a report from a stream of IOCs")

    # Feed metadata arguments.
    parser.add_argument("--name", type=str, help="Feed name", required=True)
    parser.add_argument("--owner", type=str, help="Feed owner", required=True)
    parser.add_argument("--url", type=str, help="Feed provider url", required=True)
    parser.add_argument("--summary", type=str, help="Feed summary", required=True)
    parser.add_argument("--category", type=str, help="Feed category", required=True)
    parser.add_argument("--source_label", type=str, help="Feed source label", default=None)
    parser.add_argument("--access", type=str, help="Feed access scope", default="private")

    # Report metadata arguments.
    parser.add_argument("--read_report", action="store_true", help="Read a report from stdin")
    parser.add_argument("--rep_timestamp", type=int, help="Report timestamp", default=int(time.time()))
    parser.add_argument("--rep_title", type=str, help="Report title")
    parser.add_argument("--rep_desc", type=str, help="Report description")
    parser.add_argument("--rep_severity", type=int, help="Report severity", default=1)
    parser.add_argument("--rep_link", type=str, help="Report link")
    parser.add_argument("--rep_tags", type=str, help="Report tags, comma separated")
    parser.add_argument("--rep_visibility", type=str, help="Report visibility")

    args = parser.parse_args()
    cb = get_cb_threathunter_object(args)

    feed_info = {
        "name": args.name,
        "owner": args.owner,
        "provider_url": args.url,
        "summary": args.summary,
        "category": args.category,
        "access": args.access,
    }

    reports = []
    if args.read_report:
        rep_tags = []
        if args.rep_tags:
            rep_tags = args.rep_tags.split(",")

        report = {
            "timestamp": args.rep_timestamp,
            "title": args.rep_title,
            "description": args.rep_desc,
            "severity": args.rep_severity,
            "link": args.rep_link,
            "tags": rep_tags,
            "iocs_v2": [],  # NOTE(ww): The feed server will convert IOCs to v2s for us.
        }

        report_id, iocs = read_iocs(cb)

        report["id"] = report_id
        report["iocs"] = iocs
        reports.append(report)

    feed = {
        "feedinfo": feed_info,
        "reports": reports
    }

    feed = cb.create(Feed, feed)
    feed.save()

    print(feed)


if __name__ == "__main__":
    sys.exit(main())
