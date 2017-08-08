#!/usr/bin/env python
#

import sys
from cbapi.defense import Policy
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object, get_object_by_name_or_id
from cbapi.errors import ServerError
import logging
import json

log = logging.getLogger(__name__)


def list_policies(cb, parser, args):
    for p in cb.select(Policy):
        print("Policy id {0}: {1}".format(p.id, p.name))
        print(" {0}".format(p.description))


def import_policy(cb, parser, args):
    p = cb.create(Policy)

    p.policy = json.load(open(args.policyfile, "r"))
    p.description = args.description
    p.name = args.name
    p.priorityLevel = args.prioritylevel
    p.version = 2

    try:
        p.save()
    except ServerError as se:
        print("Could not add policy: {0}".format(str(se)))
    except Exception as e:
        print("Could not add policy: {0}".format(str(e)))
    else:
        print("Added policy. New policy ID is {0}".format(p.id))


def delete_policy(cb, parser, args):
    try:
        if args.id:
            attempted_to_find = "ID of {0}".format(args.id)
            policies = [cb.select(Policy, args.id, force_init=True)]
        else:
            attempted_to_find = "name {0}".format(args.name)
            policies = [p for p in cb.select(Policy) if p.name == args.name]
            if not len(policies):
                raise Exception("No policies match")
    except Exception as e:
        print("Could not find policy with {0}: {1}".format(attempted_to_find, str(e)))
        return

    num_matching_policies = len(policies)
    if num_matching_policies > 1 and not args.force:
        print("{0:d} policies match {1:s} and --force not specified. No action taken.".format(num_matching_policies,
                                                                                              attempted_to_find))
        return

    for p in policies:
        try:
            p.delete()
        except Exception as e:
            print("Could not delete policy with {0}: {1}".format(attempted_to_find, str(e)))
        else:
            print("Deleted policy id {0} with name {1}".format(p.id, p.name))


def export_policy(cb, parser, args):
    try:
        if args.id:
            attempted_to_find = "ID of {0}".format(args.id)
            policies = [cb.select(Policy, args.id, force_init=True)]
        elif args.name:
            attempted_to_find = "name {0}".format(args.name)
            policies = [p for p in cb.select(Policy) if p.name == args.name]
            if not len(policies):
                raise Exception("No policies match")
        else:
            attempted_to_find = "all policies"
            policies = list(cb.select(Policy))

    except Exception as e:
        print("Could not find policy with {0}: {1}".format(attempted_to_find, str(e)))
        return

    for p in policies:
        json.dump(p.policy, open("policy-{0}.json".format(p.id), "w"), indent=2)
        print("Wrote policy {0} {1} to file policy-{0}.json".format(p.id, p.name))
        

def main():
    parser = build_cli_parser("Policy operations")
    commands = parser.add_subparsers(help="Policy commands", dest="command_name")

    list_command = commands.add_parser("list", help="List all configured policies")

    import_policy_command = commands.add_parser("import", help="Import policy from JSON file")
    import_policy_command.add_argument("-N", "--name", help="Name of new policy", required=True)
    import_policy_command.add_argument("-d", "--description", help="Description of new policy", required=True)
    import_policy_command.add_argument("-p", "--prioritylevel", help="Priority level (HIGH, MEDIUM, LOW)",
                                       default="LOW")
    import_policy_command.add_argument("-f", "--policyfile", help="Filename containing the JSON policy description",
                                       required=True)

    export_policy_command = commands.add_parser("export", help="Export policy to JSON file")
    export_policy_specifier = export_policy_command.add_mutually_exclusive_group(required=False)
    export_policy_specifier.add_argument("-i", "--id", type=int, help="ID of policy")
    export_policy_specifier.add_argument("-N", "--name", help="Name of policy")

    del_command = commands.add_parser("delete", help="Delete policies")
    del_policy_specifier = del_command.add_mutually_exclusive_group(required=True)
    del_policy_specifier.add_argument("-i", "--id", type=int, help="ID of policy to delete")
    del_policy_specifier.add_argument("-N", "--name", help="Name of policy to delete. Specify --force to delete"
                                         " multiple policies that have the same name")
    del_command.add_argument("--force", help="If NAME matches multiple policies, delete all matching policies",
                             action="store_true", default=False)

    args = parser.parse_args()
    cb = get_cb_defense_object(args)

    if args.command_name == "list":
        return list_policies(cb, parser, args)
    elif args.command_name == "import":
        return import_policy(cb, parser, args)
    elif args.command_name == "export":
        return export_policy(cb, parser, args)
    elif args.command_name == "delete":
        return delete_policy(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
