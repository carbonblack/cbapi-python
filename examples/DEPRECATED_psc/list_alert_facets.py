#!/usr/bin/env python

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_psc_object
from cbapi.psc.models import BaseAlert
from helpers.alertsv6 import setup_parser_with_basic_criteria, load_basic_criteria


def main():
    parser = build_cli_parser("List alert facets")
    setup_parser_with_basic_criteria(parser)
    parser.add_argument("-F", "--facet", action="append", choices=["ALERT_TYPE", "CATEGORY", "REPUTATION", "WORKFLOW",
                                                                   "TAG", "POLICY_ID", "POLICY_NAME", "DEVICE_ID",
                                                                   "DEVICE_NAME", "APPLICATION_HASH",
                                                                   "APPLICATION_NAME", "STATUS", "RUN_STATE",
                                                                   "POLICY_APPLIED_STATE", "POLICY_APPLIED",
                                                                   "SENSOR_ACTION"],
                        required=True, help="Retrieve these fields as facet information")

    args = parser.parse_args()
    cb = get_cb_psc_object(args)

    query = cb.select(BaseAlert)
    load_basic_criteria(query, args)

    facetinfos = query.facets(args.facet)
    for facetinfo in facetinfos:
        print("For field '{0}':".format(facetinfo["field"]))
        for facetval in facetinfo["values"]:
            print("\tValue {0}: {1} occurrences".format(facetval["id"], facetval["total"]))


if __name__ == "__main__":
    sys.exit(main())
