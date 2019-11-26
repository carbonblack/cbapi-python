#!/usr/bin/env python
#

import sys
import cbapi.six as six
from cbapi.response.models import Watchlist
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import logging
import json

log = logging.getLogger(__name__)


if six.PY3:
    confirm_input = input
else:
    confirm_input = raw_input  # noqa: F821


def confirm(watch_list):
    prompt = 'Import watchlist {0}? y/n: '.format(watch_list)
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


def import_watchlists(cb, args):
    if args.watchlists:
        watchlists_to_import = args.watchlists.split(",")
    else:
        watchlists_to_import = []

    watchlists = json.load(open(args.file, "r"))
    print("Importing {0} from {1}...".format(watchlists.get("ExportDescription", "<no description>"),
                                             watchlists.get("Author", "<no author>")))
    for watchlist in watchlists.get("Watchlists", []):
        if watchlists_to_import:
            if watchlist.get("Name", "") not in watchlists_to_import:
                continue

        if args.selective:
            if not confirm(watchlist.get("Name", "")):
                continue

        new_watchlist = cb.create(Watchlist)
        new_watchlist.name = watchlist.get("Name", "")
        new_watchlist.query = watchlist.get("SearchString", "")
        new_watchlist.index_type = watchlist.get("Type", "events")
        try:
            new_watchlist.save()
            print("-> Watchlist {0} added [id={1}]".format(new_watchlist.name, new_watchlist.id))
        except Exception as e:
            print("-> Watchlist {0} not added: {1}".format(new_watchlist.name, e.message))

    print("-> Done importing! <-")


def main():
    parser = build_cli_parser("Import watchlists from shareable JSON format")
    parser.add_argument("-f", "--file", help="Select what file watchlists are read from", required=True)
    parser.add_argument("-w", "--watchlists", help="Specific watchlist(s) to import. Can be comma separated.")
    parser.add_argument("-m", "--selective", action="store_true",
                        help="Interactively select which watchlists to import")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    return import_watchlists(cb, args)


if __name__ == "__main__":
    sys.exit(main())
