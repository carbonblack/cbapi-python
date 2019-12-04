#!/usr/bin/env python
#

import sys

import json
import logging

from cbapi.errors import ServerError
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object
from cbapi.psc.defense import Policy

log = logging.getLogger(__name__)


def get_policy_by_name_or_id(cb, policy_id=None, name=None, return_all_if_none=False):
    policies = []

    try:
        if policy_id:
            if isinstance(policy_id, list):
                attempted_to_find = "IDs of {0}".format(", ".join([str(pid) for pid in policy_id]))
                policies = [p for p in cb.select(Policy) if p.id in policy_id]
            else:
                attempted_to_find = "ID of {0}".format(policy_id)
                policies = [cb.select(Policy, policy_id, force_init=True)]
        elif name:
            if isinstance(name, list):
                attempted_to_find = "names of {0}".format(", ".join(name))
                policies = [p for p in cb.select(Policy) if p.name in name]
            else:
                attempted_to_find = "name {0}".format(name)
                policies = [p for p in cb.select(Policy) if p.name == name]
        elif return_all_if_none:
            attempted_to_find = "all policies"
            policies = list(cb.select(Policy))
    except Exception as e:
        print("Could not find policy with {0}: {1}".format(attempted_to_find, str(e)))

    return policies


def list_policies(cb, parser, args):
    for p in cb.select(Policy):
        print(u"Policy id {0}: {1} {2}".format(p.id, p.name, "({0})".format(p.description) if p.description else ""))
        print("Rules:")
        for r in p.rules.values():
            print("  {0}: {1} when {2} {3} is {4}".format(r.get('id'), r.get("action"),
                                                          r.get("application", {}).get("type"),
                                                          r.get("application", {}).get("value"), r.get("operation")))


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
    policies = get_policy_by_name_or_id(cb, args.id, args.name)
    if len(policies) == 0:
        return

    num_matching_policies = len(policies)
    if num_matching_policies > 1 and not args.force:
        print("{0:d} policies match and --force not specified. No action taken.".format(num_matching_policies))
        return

    for p in policies:
        try:
            p.delete()
        except Exception as e:
            print("Could not delete policy: {0}".format(str(e)))
        else:
            print("Deleted policy id {0} with name {1}".format(p.id, p.name))


def export_policy(cb, parser, args):
    policies = get_policy_by_name_or_id(cb, args.id, args.name, return_all_if_none=True)

    for p in policies:
        json.dump(p.policy, open("policy-{0}.json".format(p.id), "w"), indent=2)
        print("Wrote policy {0} {1} to file policy-{0}.json".format(p.id, p.name))


def add_rule(cb, parser, args):
    policies = get_policy_by_name_or_id(cb, args.id, args.name)

    num_matching_policies = len(policies)
    if num_matching_policies < 1:
        print("No policies match. No action taken.".format(num_matching_policies))

    for policy in policies:
        policy.add_rule(json.load(open(args.rulefile, "r")))
        print("Added rule from {0} to policy {1}.".format(args.rulefile, policy.name))


def del_rule(cb, parser, args):
    policies = get_policy_by_name_or_id(cb, args.id, args.name)

    num_matching_policies = len(policies)
    if num_matching_policies != 1:
        print("{0:d} policies match. No action taken.".format(num_matching_policies))

    policy = policies[0]
    policy.delete_rule(args.ruleid)

    print("Removed rule id {0} from policy {1}.".format(args.ruleid, policy.name))


def replace_rule(cb, parser, args):
    policies = get_policy_by_name_or_id(cb, args.id, args.name)

    num_matching_policies = len(policies)
    if num_matching_policies != 1:
        print("{0:d} policies match. No action taken.".format(num_matching_policies))

    policy = policies[0]
    policy.replace_rule(args.ruleid, json.load(open(args.rulefile, "r")))

    print("Replaced rule id {0} from policy {1} with rule from file {2}.".format(args.ruleid, policy.name,
                                                                                 args.rulefile))


def main():
    parser = build_cli_parser("Policy operations")
    commands = parser.add_subparsers(help="Policy commands", dest="command_name")

    commands.add_parser("list", help="List all configured policies")

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

    add_rule_command = commands.add_parser("add-rule", help="Add rule to existing policy from JSON rule file")
    add_rule_specifier = add_rule_command.add_mutually_exclusive_group(required=True)
    add_rule_specifier.add_argument("-i", "--id", type=int, help="ID of policy (can specify multiple)",
                                    action="append", metavar="POLICYID")
    add_rule_specifier.add_argument("-N", "--name", help="Name of policy (can specify multiple)",
                                    action="append", metavar="POLICYNAME")
    add_rule_command.add_argument("-f", "--rulefile", help="Filename containing the JSON rule", required=True)

    del_rule_command = commands.add_parser("del-rule", help="Delete rule from existing policy")
    del_rule_specifier = del_rule_command.add_mutually_exclusive_group(required=True)
    del_rule_specifier.add_argument("-i", "--id", type=int, help="ID of policy")
    del_rule_specifier.add_argument("-N", "--name", help="Name of policy")
    del_rule_command.add_argument("-r", "--ruleid", type=int, help="ID of rule", required=True)

    replace_rule_command = commands.add_parser("replace-rule", help="Replace existing rule with a new one")
    replace_rule_specifier = replace_rule_command.add_mutually_exclusive_group(required=True)
    replace_rule_specifier.add_argument("-i", "--id", type=int, help="ID of policy")
    replace_rule_specifier.add_argument("-N", "--name", help="Name of policy")
    replace_rule_command.add_argument("-r", "--ruleid", type=int, help="ID of rule", required=True)
    replace_rule_command.add_argument("-f", "--rulefile", help="Filename containing the JSON rule", required=True)

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
    elif args.command_name == "add-rule":
        return add_rule(cb, parser, args)
    elif args.command_name == "del-rule":
        return del_rule(cb, parser, args)
    elif args.command_name == "replace-rule":
        return replace_rule(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
