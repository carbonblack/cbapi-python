#!/usr/bin/env python

from cbapi.protection import Computer
from cbapi.example_helpers import get_cb_protection_object, build_cli_parser
import sys


def main():
    parser = build_cli_parser("Approve files")
    parser.add_argument("--policy", "-p", help="Policy name to use", required=True)
    parser.add_argument("--threshold", "-t", help="Prevalence threshold", default=10, type=int)
    args = parser.parse_args()

    api = get_cb_protection_object(args)

    comps = api.select(Computer).where("policyName:{0:s}".format(args.policy)).and_("deleted:false")
    for c in comps:
        changed_files = []
        files = c.fileInstances.where("localState:1")
        for f in files:
            if f.fileCatalog.prevalence >= args.threshold:
                f.localState = 2
                f.save()
                changed_files.append(f)

        if len(changed_files) > 0:
            print("Locally approved {0:d} files on computer {1:s}".format(len(changed_files), c.name))


if __name__ == '__main__':
    sys.exit(main())
