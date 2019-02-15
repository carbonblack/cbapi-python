#!/usr/bin/env python

import sys
import time
from collections import defaultdict
import validators
import hashlib

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object
from cbapi.psc.threathunter import Feed


def main():
    parser = build_cli_parser("Create a CbTH feed and report from a stream of IOCs")

    # Feed metadata arguments.
    parser.add_argument("--name", type=str, help="Feed name", required=True)
    parser.add_argument("--owner", type=str, help="Feed owner", required=True)
    parser.add_argument("--url", type=str, help="Feed provider url", required=True)
    parser.add_argument("--summary", type=str, help="Feed summary", required=True)
    parser.add_argument("--category", type=str, help="Feed category", required=True)
    parser.add_argument("--access", type=str, help="Feed access scope", default="private")

    # Report metadata arguments.
    parser.add_argument("--rep_timestamp", type=int, help="Report timestamp", default=int(time.time()))
    parser.add_argument("--rep_title", type=str, help="Report title", required=True)
    parser.add_argument("--rep_desc", type=str, help="Report description", required=True)
    parser.add_argument("--rep_severity", type=int, help="Report severity", default=1)
    parser.add_argument("--rep_link", type=str, help="Report link")
    parser.add_argument("--rep_tags", type=str, help="Report tags, comma separated")
    parser.add_argument("--rep_visibility", type=str, help="Report visibility")

    args = parser.parse_args()
    cb = get_cb_threathunter_feed_object(args)

    feed_info = {
        "name": args.name,
        "owner": args.owner,
        "provider_url": args.url,
        "summary": args.summary,
        "category": args.category,
        "access": args.access,
    }

    iocs = defaultdict(list)

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

    report_id = hashlib.md5()
    report_id.update(str(time.time()).encode("utf-8"))

    # TODO(ww): Instead of validating here, create an IOCs
    # object, populate it with these, and run _validate()
    for idx, line in enumerate(sys.stdin):
        line = line.rstrip("\r\n")
        report_id.update(line.encode("utf-8"))
        if validators.md5(line):
            iocs["md5"].append(line)
        elif validators.sha256(line):
            iocs["sha256"].append(line)
        elif validators.ipv4(line):
            iocs["ipv4"].append(line)
        elif validators.ipv6(line):
            iocs["ipv6"].append(line)
        elif validators.domain(line):
            iocs["dns"].append(line)
        else:
            # TODO(ww): Which endpoint should we use for query validation?
            # The Process query validation endpoint doesn't work.
            print("line {}: invalid IOC and/or query".format(idx + 1))
            # if cb.validate_query(line):
            #     query_ioc = {"search_query": line}
            #     iocs["query"].append(query_ioc)
            # else:
            #     print("line {}: invalid query".format(idx + 1))
            #     return 1

    report["id"] = report_id.hexdigest()
    report["iocs"] = dict(iocs)

    feed = {
        "feedinfo": feed_info,
        "reports": [report]
    }

    feed = cb.create(Feed, feed)
    feed.save()

    print(feed)


if __name__ == "__main__":
    sys.exit(main())
