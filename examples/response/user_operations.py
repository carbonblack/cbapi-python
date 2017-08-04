#!/usr/bin/env python
#

import sys
from cbapi.response.models import User
from cbapi.example_helpers import build_cli_parser, get_cb_response_object, get_object_by_name_or_id
from cbapi.errors import ServerError
import logging
import getpass
from cbapi.response.rest_api import get_api_token


log = logging.getLogger(__name__)


def list_users(cb, parser, args):
    for u in cb.select(User):
        print(u)
        print("")


def add_user(cb, parser, args):
    u = cb.create(User)
    u.username = args.username
    u.first_name = args.first_name
    u.last_name = args.last_name
    u.password = args.password
    u.email = args.email
    u.teams = []
    u.global_admin = args.global_admin

    log.debug("Adding user: {0:s}".format(u.username))

    try:
        u.save()
    except ServerError as se:
        print("Could not add user: {0:s}".format(str(se)))
    except Exception as e:
        print("Could not add user: {0:s}".format(str(e)))
    else:
        log.debug("user data: {0:s}".format(str(u)))
        print("Added user {0}.".format(u.username))


def delete_user(cb, parser, args):
    user = cb.select(User, args.name)
    try:
        user.delete()
    except Exception as e:
        print("Could not delete user {0:s}: {1:s}".format(args.name, str(e)))
    else:
        print("Deleted user {0:s}".format(args.name))


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="User commands", dest="command_name")

    list_command = commands.add_parser("list", help="List all configured users")

    add_command = commands.add_parser("add", help="Add new user")
    add_command.add_argument("-N", "--name", help="username", required=True)
    add_command.add_argument("-q", "--query", help="user query string, e.g. process_name:notepad.exe",
                             required=True)
    add_command.add_argument("-t", "--type", help="user type 'events' or 'modules'", required=True)

    del_command = commands.add_parser("delete", help="Delete user")
    del_user_specifier = del_command.add_mutually_exclusive_group(required=True)
    del_user_specifier.add_argument("-N", "--name", help="Name of user to delete.")

    get_api_key_command = commands.add_parser("get-api-key", help="Get API key for a user")
    get_api_key_command.add_argument("-N", "--name", help="username", required=True)

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    if args.command_name == "list":
        return list_users(cb, parser, args)
    elif args.command_name == "add":
        return add_user(cb, parser, args)
    elif args.command_name == "delete":
        return delete_user(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
