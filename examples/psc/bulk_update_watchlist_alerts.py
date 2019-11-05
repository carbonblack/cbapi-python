#!/usr/bin/env python

import sys
from time import sleep
from cbapi.example_helpers import build_cli_parser, get_cb_psc_object
from cbapi.psc.models import WatchlistAlert
from alertsv6common import setup_parser_with_watchlist_criteria, load_watchlist_criteria

def main():
    parser = build_cli_parser("Bulk update the status of watchlist alerts")
    setup_parser_with_watchlist_criteria(parser)
    parser.add_argument("-R", "--remediation", help="Remediation message to store for the selected alerts")
    parser.add_argument("-C", "--comment", help="Comment message to store for the selected alerts")
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--dismiss", action="store_true", help="Dismiss all selected alerts")
    operation.add_argument("--undismiss", action="store_true", help="Undismiss all selected alerts")
    
    args = parser.parse_args()
    cb = get_cb_psc_object(args)
    
    if args.dismiss:
        query = cb.bulk_alert_dismiss("WATCHLIST")
    elif args.undismiss:
        query = cb.bulk_alert_undismiss("WATCHLIST")
    else:
        raise NotImplemented("one of --dismiss or --undismiss must be specified")
    
    load_watchlist_criteria(query, args)

    if args.remediation:
        query = query.remediation(args.remediation)
    if args.comment:
        query = query.comment(args.comment)
    statobj = query.run()
    print("Submitted query with ID {0}".format(statobj.id_))
    while not statobj.finished:
        print("Waiting...")
        sleep(1)
    if statobj.errors:
        print("Errors encountered:")
        for err in statobj.errors:
            print("\t{0}".format(err))
    if statobj.failed_ids:
        print("Failed alert IDs:")
        for i in statobj.failed_ids:
            print("\t{0}".format(err))
    print("{0} total alert(s) found, of which {1} were successfully changed" \
          .format(statobj.num_hits, statobj.num_success))


if __name__ == "__main__":
    sys.exit(main())
