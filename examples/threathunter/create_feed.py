#!/usr/bin/env python

import sys
import time
from collections import defaultdict
import validators

from cbapi.example_helpers import build_cli_parser, get_cb_threathunter_feed_object
from cbapi.psc.threathunter import Feed


def main():
    parser = build_cli_parser("Create a CbTH feed from a stream of IOCs")

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
        'name': args.name,
        'owner': args.owner,
        'provider_url': args.url,
        'summary': args.summary,
        'category': args.category,
        'access': args.access,
    }

    iocs = defaultdict(list)

    rep_tags = []
    if args.rep_tags:
        rep_tags = args.rep_tags.split(",")

    report = {
        'timestamp': args.rep_timestamp,
        'title': args.rep_title,
        'description': args.rep_desc,
        'severity': args.rep_severity,
        'link': args.rep_link,
        'tags': rep_tags,
        'iocs': iocs,
    }

    for _idx, line in enumerate(sys.stdin):
        line = line.rstrip("\r\n")
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
            # TODO(ww): Validate queries.
            # Can we use the CbTH process search validation endpoint?
            pass

    feed = {
        'feedinfo': feed_info,
        'reports': [report]
    }

    feed = cb.create(Feed, feed)

    print(feed)


if __name__ == "__main__":
    sys.exit(main())
