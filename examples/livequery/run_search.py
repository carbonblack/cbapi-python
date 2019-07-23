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
        "--statuses",
        nargs="+",
        type=str,
        required=False,
        help="Statuses to filter on",
    )
    parser.add_argument(
        "-S", "--sort_by", type=str, help="sory by this field", required=False
    )
    parser.add_argument(
        "-D",
        "--descending_results",
        help="return results in descending order",
        action="store_true",
    )

    args = parser.parse_args()
    cb = get_cb_livequery_object(args)

    results = cb.select(Result).run_id(args.id)
    if args.query:
        results = results.where(args.query)

    if args.device_ids:
        results.criteria(device_id=args.device_ids)
    if args.device_types:
        results.criteria(device_type=args.device_types)
    if args.statuses:
        results.criteria(status=args.statuses)

    if args.sort_by:
        direction = "ASC"
        if args.descending_results:
            direction = "DESC"
        results.sort_by(args.sort_by, direction=direction)

    for result in results:
        if args.fields_only:
            print(result.fields_)
        else:
            print(result)


if __name__ == "__main__":
    sys.exit(main())
