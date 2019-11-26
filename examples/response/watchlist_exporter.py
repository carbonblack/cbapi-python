#!/usr/bin/env python
#

import sys
import cbapi.six as six
from cbapi.response.models import Watchlist
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import logging
from datetime import datetime
import json

log = logging.getLogger(__name__)


if six.PY3:
    confirm_input = input
else:
    confirm_input = raw_input  # noqa: F821


def confirm(watch_list):
    prompt = 'Export watchlist {0}? y/n: '.format(watch_list)
    while True:
        answer = confirm_input(prompt)
        if not answer:
            return True
        if answer not in ['y', 'Y', 'n', 'N']:
            print('Please enter y or n.')
            continue
        if answer in ['Y', 'y']:
            return True
        if answer in ['N', 'n']:
            return False


def export_watchlists(cb, args):
    exported_watchlists = []

    if args.watchlists:
        watchlists_to_export = args.watchlists.split(",")
    else:
        watchlists_to_export = []

    for watchlist in cb.select(Watchlist):
        if watchlists_to_export:
            if watchlist.name not in watchlists_to_export:
                continue

        if args.selective:
            if not confirm(watchlist.name):
                continue

        exported_watchlists.append(
            {
                "Name": watchlist.name,
                "URL": watchlist.search_query,
                "Type": watchlist.index_type,
                "SearchString": watchlist.query,
                "Description": "Please fill in if you intend to share this."
            }
        )

    export = {
        "Author": args.author or "Fill in author",
        "ExportDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ExportDescription": args.description or "Fill in description",
        "Watchlists": exported_watchlists,
    }

    json.dump(export, open(args.file, "w"), indent=4)
    print("-> Done exporting! <-")


def main():
    parser = build_cli_parser("Export watchlists into shareable JSON format")
    parser.add_argument("-f", "--file", help="Select what file output is written to", required=True)
    parser.add_argument("-w", "--watchlists", help="Specific watchlist(s) to export. Can be comma separated.")
    parser.add_argument("-m", "--selective", action="store_true",
                        help="Interactively select which watchlists to export")
    parser.add_argument("-d", "--description", help="Description for the watchlist export file")
    parser.add_argument("-a", "--author", help="Author for the watchlist export file")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    return export_watchlists(cb, args)


if __name__ == "__main__":
    sys.exit(main())
