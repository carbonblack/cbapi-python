#!/usr/bin/env python

import sys
from time import sleep
from cbapi.example_helpers import build_cli_parser, get_cb_psc_object
from cbapi.psc.models import BaseAlert, WorkflowStatus
from helpers.alertsv6 import setup_parser_with_basic_criteria, load_basic_criteria


def main():
    parser = build_cli_parser("Bulk update the status of alerts")
    setup_parser_with_basic_criteria(parser)
    parser.add_argument("-R", "--remediation", help="Remediation message to store for the selected alerts")
    parser.add_argument("-C", "--comment", help="Comment message to store for the selected alerts")
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--dismiss", action="store_true", help="Dismiss all selected alerts")
    operation.add_argument("--undismiss", action="store_true", help="Undismiss all selected alerts")

    args = parser.parse_args()
    cb = get_cb_psc_object(args)

    query = cb.select(BaseAlert)
    load_basic_criteria(query, args)

    if args.dismiss:
        reqid = query.dismiss(args.remediation, args.comment)
    elif args.undismiss:
        reqid = query.update(args.remediation, args.comment)
    else:
        raise NotImplementedError("one of --dismiss or --undismiss must be specified")

    print("Submitted query with ID {0}".format(reqid))
    statobj = cb.select(WorkflowStatus, reqid)
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
    print("{0} total alert(s) found, of which {1} were successfully changed"
          .format(statobj.num_hits, statobj.num_success))


if __name__ == "__main__":
    sys.exit(main())
