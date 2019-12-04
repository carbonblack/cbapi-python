import sys

from cbapi.example_helpers import build_cli_parser, get_cb_livequery_object
from cbapi.psc.livequery.models import Result


def main():
    parser = build_cli_parser("Search the device summaries of a LiveQuery run")
    parser.add_argument("-i", "--id", type=str, required=True, help="Run ID")
    parser.add_argument("-q", "--query", type=str, required=False, help="Search query")

    parser.add_argument(
        "--device_ids",
        nargs="+",
        type=int,
        required=False,
        help="Device IDs to filter on",
    )
    parser.add_argument(
        "--device_names",
        nargs="+",
        type=int,
        required=False,
        help="Device names to filter on",
    )
    parser.add_argument(
        "--policy_ids",
        nargs="+",
        type=int,
        required=False,
        help="Policy IDs to filter on",
    )
    parser.add_argument(
        "--policy_names",
        nargs="+",
        type=int,
        required=False,
        help="Policy names to filter on",
    )
    parser.add_argument(
        "--statuses",
        nargs="+",
        type=str,
        required=False,
        help="Statuses to filter on",
    )
    parser.add_argument(
        "-S", "--sort_by", type=str, help="sort by this field", required=False
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
    result = results.first()
    if result is None:
        print("ERROR: No results.")
        return 1

    summaries = result.query_device_summaries()
    if args.query:
        summaries.where(args.query)
    if args.device_ids:
        summaries.criteria(device_id=args.device_ids)
    if args.device_names:
        summaries.criteria(device_name=args.device_names)
    if args.policy_ids:
        summaries.criteria(policy_id=args.policy_ids)
    if args.policy_names:
        summaries.criteria(policy_name=args.policy_names)
    if args.statuses:
        summaries.criteria(status=args.statuses)
    if args.sort_by:
        dir = "DESC" if args.descending_results else "ASC"
        summaries.sort_by(args.sort_by, direction=dir)

    for summary in summaries:
        print(summary)


if __name__ == "__main__":
    sys.exit(main())
