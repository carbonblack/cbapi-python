import sys

from cbapi.example_helpers import build_cli_parser, get_cb_livequery_object
from cbapi.psc.livequery.models import Run


def create_run(cb, args):
    query = cb.query(args.sql)

    if args.device_ids:
        query.device_ids(args.device_ids)
    if args.device_types:
        query.device_types(args.device_types)
    if args.policy_ids:
        query.policy_ids(args.policy_ids)
    if args.notify:
        query.notify_on_finish()
    if args.name:
        query.name(args.name)

    run = query.submit()
    print(run)


def run_status(cb, args):
    run = cb.select(Run, args.id)
    print(run)


def main():
    parser = build_cli_parser("Create and manage LiveQuery runs")
    commands = parser.add_subparsers(help="Commands", dest="command_name")

    create_command = commands.add_parser("create", help="Create a new LiveQuery run")
    create_command.add_argument(
        "-s", "--sql", type=str, required=True, help="The query to run"
    )
    create_command.add_argument(
        "-n",
        "--notify",
        action="store_true",
        help="Notify by email when the run finishes",
    )
    create_command.add_argument(
        "-N", "--name", type=str, required=False, help="The name of the run"
    )
    create_command.add_argument(
        "--device_ids",
        nargs="+",
        type=int,
        required=False,
        help="Device IDs to filter on",
    )
    create_command.add_argument(
        "--device_types",
        nargs="+",
        type=str,
        required=False,
        help="Device types to filter on",
    )
    create_command.add_argument(
        "--policy_ids",
        nargs="+",
        type=str,
        required=False,
        help="Policy IDs to filter on",
    )

    status_command = commands.add_parser(
        "status", help="Retrieve information about a run"
    )
    status_command.add_argument(
        "-i", "--id", type=str, required=True, help="The run ID"
    )

    args = parser.parse_args()
    cb = get_cb_livequery_object(args)

    if args.command_name == "create":
        return create_run(cb, args)
    elif args.command_name == "status":
        return run_status(cb, args)


if __name__ == "__main__":
    sys.exit(main())
