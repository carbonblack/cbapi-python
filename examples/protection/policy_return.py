from cbapi.example_helpers import get_cb_protection_object, build_cli_parser
from cbapi.protection.models import Computer, Policy
import sys


def main():
    parser = build_cli_parser("Revert computers in policy to previous policy")
    parser.add_argument("--policy", "-p", help="Policy name or ID", required=True)
    args = parser.parse_args()

    p = get_cb_protection_object(args)

    try:
        policyId = int(args.policy)
    except ValueError:
        policyId = p.select(Policy).where("name:{}".format(args.policy)).id

    for computer in p.select(Computer).where("policyId:{}".format(policyId)):
        print("%s was in %s" % (computer.name, computer.policyName))
        computer.policyId = computer.previousPolicyId
        computer.save()
        print("%s is now in %s" % (computer.name, computer.policyName))


if __name__ == '__main__':
    sys.exit(main())
