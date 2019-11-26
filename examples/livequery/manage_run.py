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


def run_stop(cb, args):
    run = cb.select(Run, args.id)
    if run.stop():
        print("Run {} has been stopped.".format(run.id))
        print(run)
    else:
        print("Unable to stop run {}".format(run.id))


def run_delete(cb, args):
    run = cb.select(Run, args.id)
    if run.delete():
        print("Run {} has been deleted.".format(run.id))
    else:
        print("Unable to delete run {}".format(run.id))


def run_history(cb, args):
    results = cb.query_history(args.query)
    if args.sort_by:
        dir = "DESC" if args.descending_results else "ASC"
        results.sort_by(args.sort_by, direction=dir)
    for result in results:
        print(result)


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

    stop_command = commands.add_parser(
        "stop", help="Stops/cancels a current run"
    )
    stop_command.add_argument(
        "-i", "--id", type=str, required=True, help="The run ID"
    )

    delete_command = commands.add_parser(
        "delete", help="Permanently delete a run"
    )
    delete_command.add_argument(
        "-i", "--id", type=str, required=True, help="The run ID"
    )

    history_command = commands.add_parser(
        "history", help="List history of all runs"
    )
    history_command.add_argument(
        "-q", "--query", type=str, required=False, help="Query string to use"
    )
    history_command.add_argument(
        "-S", "--sort_by", type=str, help="sort by this field", required=False
    )
    history_command.add_argument(
        "-D",
        "--descending_results",
        help="return results in descending order",
        action="store_true",
        required=False
    )

    args = parser.parse_args()
    cb = get_cb_livequery_object(args)

    if args.command_name == "create":
        return create_run(cb, args)
    elif args.command_name == "status":
        return run_status(cb, args)
    elif args.command_name == "stop":
        return run_stop(cb, args)
    elif args.command_name == "delete":
        return run_delete(cb, args)
    elif args.command_name == "history":
        return run_history(cb, args)


if __name__ == "__main__":
    sys.exit(main())
