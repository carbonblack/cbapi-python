import sys

from cbapi.example_helpers import build_cli_parser, get_cb_livequery_object
from cbapi.psc.livequery.models import Result


def main():
    parser = build_cli_parser("Search the facets of a LiveQuery run")
    parser.add_argument("-i", "--id", type=str, required=True, help="Run ID")
    parser.add_argument(
        "--result",
        action="store_true",
        help="Run facet query on results"
    )
    parser.add_argument(
        "--device_summary",
        action="store_true",
        help="Run facet query on device summaries"
    )
    parser.add_argument(
        "-f",
        "--fields",
        nargs="+",
        type=str,
        required=False,
        help="Fields to be displayed in results",
    )

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

    args = parser.parse_args()
    if not (args.result or args.device_summary):
        print("ERROR: One of --result or --device_summary must be specified")
        return 1
    if args.result and args.device_summary:
        print("ERROR: --result and --device_summary cannot both be specified")
        return 1

    cb = get_cb_livequery_object(args)

    results = cb.select(Result).run_id(args.id)
    result = results.first()
    if result is None:
        print("ERROR: No results.")
        return 1

    if args.result:
        facets = result.query_result_facets()
    elif args.device_summary:
        facets = result.query_device_summary_facets()
    if args.fields:
        facets.facet_field(args.fields)
    if args.query:
        facets.where(args.query)
    if args.device_ids:
        facets.criteria(device_id=args.device_ids)
    if args.device_names:
        facets.criteria(device_name=args.device_names)
    if args.policy_ids:
        facets.criteria(policy_id=args.policy_ids)
    if args.policy_names:
        facets.criteria(policy_name=args.policy_names)
    if args.statuses:
        facets.criteria(status=args.statuses)

    for facet in facets:
        print(facet)


if __name__ == "__main__":
    sys.exit(main())
