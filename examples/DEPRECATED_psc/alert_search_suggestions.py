#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_psc_object


def main():
    parser = build_cli_parser("Get suggestions for searching alerts")
    parser.add_argument("-q", "--query", default="", help="Query string for looking for alerts")

    args = parser.parse_args()
    cb = get_cb_psc_object(args)

    suggestions = cb.alert_search_suggestions(args.query)
    for suggestion in suggestions:
        print("Search term: '{0}'".format(suggestion["term"]))
        print("\tWeight: {0}".format(suggestion["weight"]))
        print("\tAvailable with products: {0}".format(", ".join(suggestion["required_skus_some"])))


if __name__ == "__main__":
    sys.exit(main())
