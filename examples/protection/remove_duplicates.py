from cbapi.example_helpers import get_cb_protection_object, build_cli_parser
from cbapi.protection.models import Computer
from collections import defaultdict
import sys
from six import iteritems


def main():
    parser = build_cli_parser("Delete duplicate computers")
    parser.add_argument("--dry-run", "-d", help="perform a dry run, don't actually delete the computers",
                        action="store_true", dest="dry_run")

    args = parser.parse_args()
    p = get_cb_protection_object(args)

    computer_list = defaultdict(list)
    for computer in p.select(Computer).where("deleted:false"):
        computer_list[computer.name].append({"id": computer.id, "offline": computer.daysOffline})

    for computer_name, computer_ids in iteritems(computer_list):
        if len(computer_ids) > 1:
            sorted_computers = sorted(computer_ids, key=lambda x: x["offline"], reverse=True)
            for computer_id in sorted_computers[:-1]:
                if computer_id["offline"] > 0:
                    print("deleting computer id %d (offline %d days, hostname %s)" % (computer_id["id"],
                                                                                      computer_id["offline"],
                                                                                      computer_name))
                    if not args.dry_run:
                        print("deleting from server...")
                        p.select(Computer, computer_id["id"]).delete()

if __name__ == '__main__':
    sys.exit(main())
