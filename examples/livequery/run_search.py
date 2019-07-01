import sys

from cbapi.example_helpers import build_cli_parser, get_cb_livequery_object
from cbapi.psc.livequery.models import Result


def main():
    parser = build_cli_parser("Search the results of a LiveQuery run")
    parser.add_argument("-i", "--id", type=str, required=True, help="Run ID")
    parser.add_argument("-q", "--query", type=str, required=False, help="Search query")
    parser.add_argument(
        "-F", "--fields_only", action="store_true", help="Show only fields"
    )
    parser.add_argument(
        "--device_ids",
        nargs="+",
        type=int,
        required=False,
        help="Device IDs to filter on",
    )
    parser.add_argument(
        "--device_types",
        nargs="+",
        type=str,
        required=False,
        help="Device types to filter on",
    )
    parser.add_argument(
        "--policy_ids",
        nargs="+",
        type=str,
        required=False,
        help="Policy IDs to filter on",
    )

    # TODO(ww): Flags for criteria, sort_by

    args = parser.parse_args()
    cb = get_cb_livequery_object(args)

    results = cb.select(Result).run_id(args.id)
    if args.query:
        results = results.where(args.query)

    if args.device_ids:
        results.criteria(device_ids=args.device_ids)
    if args.device_types:
        results.criteria(device_types=args.device_types)
    if args.policy_ids:
        results.criteria(policy_ids=args.policy_ids)

    for result in results:
        if args.fields_only:
            print(result.fields_)
        else:
            print(result)


if __name__ == "__main__":
    sys.exit(main())
