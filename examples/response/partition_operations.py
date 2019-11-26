import sys
from distutils.version import LooseVersion

from cbapi.response.models import StoragePartition
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import logging

log = logging.getLogger(__name__)


def list_partitions(cb, parser, args):
    for partition in cb.select(StoragePartition):
        print('{0} Storage Partition "{1}":'.format(partition.status.upper(), partition.name))
        for partition_info in partition.info:
            print("  {0:15s}: {1}".format(partition_info, partition.info[partition_info]))


def create_partition(cb, parser, args):
    cb.create_new_partition()
    print("Successfully created new writer partition")


def delete_partition(cb, parser, args):
    # select the partition by name (which same as the ID)
    try:
        partition = cb.select(StoragePartition, args.name)
        partition.delete()
    except Exception as e:
        print("Error deleting partition {0}: {1}".format(args.name, str(e)))
    else:
        print("Successfully deleted partition {0}".format(args.name))


def mount_partition(cb, parser, args):
    # select the partition by name (which same as the ID)
    try:
        partition = cb.select(StoragePartition, args.name)
        partition.mount()
    except Exception as e:
        print("Error mounting partition {0}: {1}".format(args.name, str(e)))
    else:
        print("Successfully mounted partition {0}".format(args.name))


def unmount_partition(cb, parser, args):
    # select the partition by name (which same as the ID)
    try:
        partition = cb.select(StoragePartition, args.name)
        partition.unmount()
    except Exception as e:
        print("Error unmounting partition {0}: {1}".format(args.name, str(e)))
    else:
        print("Successfully unmounted partition {0}".format(args.name))


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="Storage Partition commands", dest="command_name")

    commands.add_parser("list", help="List all storage partitions")

    commands.add_parser("create", help="Create new active writer partition")

    del_command = commands.add_parser("delete", help="Delete partition")
    del_command.add_argument("-N", "--name", help="Name of partition to delete.", required=True)

    mount_command = commands.add_parser("mount", help="Mount partition")
    mount_command.add_argument("-N", "--name", help="Name of partition to mount.", required=True)

    unmount_command = commands.add_parser("unmount", help="Unmount partition")
    unmount_command.add_argument("-N", "--name", help="Name of partition to unmount.", required=True)

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    if cb.cb_server_version < LooseVersion("6.1.0"):
        parser.error("This script can only work with server versions >= 6.1.0; {0} is running {1}"
                     .format(cb.url, cb.cb_server_version))
        return 1

    if args.command_name == "list":
        return list_partitions(cb, parser, args)
    elif args.command_name == "create":
        return create_partition(cb, parser, args)
    elif args.command_name == "delete":
        return delete_partition(cb, parser, args)
    elif args.command_name == "mount":
        return mount_partition(cb, parser, args)
    elif args.command_name == "unmount":
        return unmount_partition(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
