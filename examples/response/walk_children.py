#!/usr/bin/env python

from cbapi.response import Process
from cbapi.errors import ApiError, ObjectNotFoundError
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import sys


# This function is called for every child of the given process
def visitor(proc, depth):
    try:
        print("%s%s: %s" % ('  '*(depth-1), proc.start, proc.cmdline))
    except Exception as e:
        print("** Encountered error while walking children: {0:s}".format(str(e)))


def main():
    parser = build_cli_parser("Walk the children of a given process")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--process", "-p", help="process GUID to walk", default='')
    group.add_argument("--query", "-q", help="walk the children of all processes matching this query")
    args = parser.parse_args()
    c = get_cb_response_object(args)

    if args.process:
        try:
            procs = [c.select(Process, args.process, force_init=True)]
        except ObjectNotFoundError as e:
            print("Could not find process {0:s}".format(args.procss))
            return 1
        except ApiError as e:
            print("Encountered error retrieving process: {0:s}".format(str(e)))
            return 1
        except Exception as e:
            print("Encountered unknown error retrieving process: {0:s}".format(str(e)))
            return 1
    elif args.query:
        procs = c.select(Process).where(args.query)
    else:
        print("Requires either a --process or --query argument")
        parser.print_usage()
        return 2

    for root_proc in procs:
        print("Process {0:s} on {1:s} executed by {2:s} children:".format(root_proc.path, root_proc.hostname,
                                                                          root_proc.username))
        root_proc.walk_children(visitor)
        print("")


if __name__ == '__main__':
    sys.exit(main())
