#!/usr/bin/env python
#

import sys
from cbapi.response.models import User, Team, SensorGroup
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
from cbapi.errors import ServerError
import logging
import getpass


log = logging.getLogger(__name__)


def list_users(cb, parser, args):
    format_string = "{:16s} {:30s} {:30s} {:40s}"
    print(format_string.format("Username", "Name", "Email address", "Teams"))
    print(format_string.format("-"*16, "-"*30, "-"*30, "-"*40))

    for u in cb.select(User):
        print(format_string.format(u.username, " ".join([u.first_name, u.last_name]), u.email,
                                   ", ".join([t['name'] for t in u.teams])))


def list_teams(cb, parser, args):
    for t in cb.select(Team):
        print("Team {0} (id {1}):".format(t.name, t.id))
        for ga in t.group_access:
            print("  {0} on Sensor Group \"{1}\"".format(ga["access_category"], ga["group_name"]))


def add_team(cb, parser, args):
    t = cb.create(Team)
    t.name = args.name

    for sg in args.administrator or []:
        if isinstance(t, int):
            sg = cb.select(SensorGroup, sg)
        else:
            sg = cb.select(SensorGroup).where("name:{0}".format(sg)).first()

        t.add_administrator_access(sg)

    for sg in args.viewer or []:
        if isinstance(t, int):
            sg = cb.select(SensorGroup, sg)
        else:
            sg = cb.select(SensorGroup).where("name:{0}".format(sg)).first()

        t.add_viewer_access(sg)

    try:
        t.save()
    except ServerError as se:
        print("Could not add team: {0:s}".format(str(se)))
    except Exception as e:
        print("Could not add team: {0:s}".format(str(e)))
    else:
        log.debug("team data: {0:s}".format(str(t)))
        print("Added team {0}.".format(t.name))


def add_user(cb, parser, args):
    u = cb.create(User)
    u.username = args.username
    u.first_name = args.first_name
    u.last_name = args.last_name
    u.email = args.email
    u.teams = []
    u.global_admin = args.global_admin

    log.debug("Adding user: {0:s}".format(u.username))

    if not args.password:
        passwords_dont_match = True
        while passwords_dont_match:
            pw1 = getpass.getpass("New password for {0}: ".format(u.username))
            pw2 = getpass.getpass("Re-enter password: ")
            if pw1 == pw2:
                passwords_dont_match = False
            else:
                print("Passwords don't match; try again")

        u.password = pw1
    else:
        u.password = args.password

    for t in args.team or []:
        if isinstance(t, int):
            t = cb.select(Team, t)
        else:
            t = cb.select(Team).where("name:{0}".format(t)).first()

        u.add_team(t)

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
    user = cb.select(User, args.username)
    try:
        user.delete()
    except Exception as e:
        print("Could not delete user {0:s}: {1:s}".format(args.username, str(e)))
    else:
        print("Deleted user {0:s}".format(args.username))


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="User commands", dest="command_name")

    commands.add_parser("list", help="List all configured users")
    commands.add_parser("list-teams", help="List all configured user teams")

    add_command = commands.add_parser("add", help="Add new user")
    add_command.add_argument("-u", "--username", help="New user's username", required=True)
    add_command.add_argument("-f", "--first-name", help="First name", required=True)
    add_command.add_argument("-l", "--last-name", help="Last name", required=True)
    add_command.add_argument("-p", "--password", help="Password - if not specified, prompt at runtime", required=False)
    add_command.add_argument("-e", "--email", help="Email address", required=True)
    add_command.add_argument("-A", "--global-admin", help="Make new user global admin", default=False,
                             action="store_true")
    add_command.add_argument("-t", "--team", help="Add new user to this team (can specify multiple teams)",
                             action="append", metavar="TEAM-NAME")

    add_team_command = commands.add_parser("add-team", help="Add new team")
    add_team_command.add_argument("-N", "--name", help="Name of the new team")
    add_team_command.add_argument("-A", "--administrator", help="Add administrator rights to the given sensor group",
                                  metavar="SENSOR-GROUP", action="append")
    add_team_command.add_argument("-V", "--viewer", help="Add viewer rights to the given sensor group",
                                  metavar="SENSOR-GROUP", action="append")

    get_api_key_command = commands.add_parser("get-api-key", help="Get API key for user")
    get_api_key_command.add_argument("-u", "--username", help="Username", required=True)
    get_api_key_command.add_argument("-p", "--password", help="Password - if not specified, prompt at runtime",
                                     required=False)

    del_command = commands.add_parser("delete", help="Delete user")
    del_user_specifier = del_command.add_mutually_exclusive_group(required=True)
    del_user_specifier.add_argument("-u", "--username", help="Name of user to delete.")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    if args.command_name == "list":
        return list_users(cb, parser, args)
    elif args.command_name == "list-teams":
        return list_teams(cb, parser, args)
    elif args.command_name == "add":
        return add_user(cb, parser, args)
    elif args.command_name == "add-team":
        return add_team(cb, parser, args)
    elif args.command_name == "delete":
        return delete_user(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
