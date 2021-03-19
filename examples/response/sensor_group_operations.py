#!/usr/bin/env python
#

import sys
from cbapi.response.models import SensorGroup, Site
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
from cbapi.errors import ServerError
import logging

log = logging.getLogger(__name__)


def list_sensor_groups(cb, parser, args):
    for g in cb.select(SensorGroup):
        print(g)
        print("")


def list_sensors(cb, parser, args):
    if args.group_name:
        group = cb.select(SensorGroup).where("name:{0}".format(args.group_name)).first()
    else:
        group = min(cb.select(SensorGroup), key=lambda x: x.id)

    print("Sensors in group {0} (id {1}):".format(group.name, group.id))
    print("  {0:40}{1:18}{2}".format("Hostname", "IP Address", "Last Checkin Time"))
    for sensor in group.sensors:
        ipaddrs = [iface.ipaddr for iface in sensor.network_interfaces if iface.ipaddr not in ("127.0.0.1", "0.0.0.0")]
        print("  {0:40}{1:18}{2}".format(sensor.hostname,
                                         ipaddrs[0] if len(ipaddrs) else '',
                                         sensor.last_checkin_time))


def add_sensor_group(cb, parser, args):
    g = cb.create(SensorGroup)

    if args.site_name:
        site = cb.select(Site).where("name:{0}".format(args.site_name)).first()
        if not site:
            print("Could not find site named {0}".format(args.site_name))
            return 1
    elif args.site_id:
        site = cb.select(Site).where("id:{0}".format(args.site_id)).first()
        if not site:
            print("Could not find site ID {0}".format(args.site_id))
            return 1
    else:
        # Just pick the first site by the lowest ID
        site = min(cb.select(Site), key=lambda x: x.id)

    g.name = args.new_group_name
    g.site = site
    g.sensorbackend_server = args.sensorbackend_server
    g.sensor_version_windows = g.sensor_version_linux = g.sensor_version_osx = 'Manual'

    try:
        g.save()
    except ServerError as se:
        print("Received HTTP error {0} when attempting to add sensor group: {1}".format(se.error_code, str(se)))
    except Exception as e:
        print("Could not add sensor group: {0:s}".format(str(e)))
    else:
        log.debug("New Sensor Group: {0:s}".format(str(g)))
        print("Added sensor group. New sensor group ID is {0:d}".format(g.id))


def delete_sensor_group(cb, parser, args):
    try:
        if args.id:
            attempted_to_find = "ID of {0:d}".format(args.id)
            groups = [cb.select(SensorGroup, args.id, force_init=True)]
        else:
            attempted_to_find = "name {0:s}".format(args.groupname)
            groups = cb.select(SensorGroup).where("name:{0:s}".format(args.groupname))[::]
            if not len(groups):
                raise Exception("No sensor groups match")
    except Exception as e:
        print("Could not find sensor group with {0:s}: {1:s}".format(attempted_to_find, str(e)))
        return

    num_matching_sensor_groups = len(groups)
    if num_matching_sensor_groups > 1 and not args.force:
        print("{0:d} sensor groups match {1:s} and --force not specified. No action taken."
              .format(num_matching_sensor_groups, attempted_to_find))
        return

    for g in groups:
        try:
            g.delete()
        except Exception as e:
            print("Could not delete sensor group with {0:s}: {1:s}".format(attempted_to_find, str(e)))
        else:
            print("Deleted sensor group id {0:d} with name {1:s}".format(g.id, g.name))


def main():
    parser = build_cli_parser()
    commands = parser.add_subparsers(help="Sensor Group commands", dest="command_name")

    commands.add_parser("list", help="List all configured sensor groups")

    add_command = commands.add_parser("add", help="Add new sensor group")
    add_command.add_argument("-n", "--name", action="store", help="Sensor group name", required=True,
                             dest="new_group_name")
    site_group = add_command.add_mutually_exclusive_group(required=False)
    site_group.add_argument("-s", "--site", action="store", help="Site name", dest="site_name")
    site_group.add_argument("-i", "--site-id", action="store", help="Site ID", dest="site_id")
    add_command.add_argument("-b", "--sensorbackend-server", action="store", help="Sensor backend server", required=True,
                             dest="sensorbackend_server")

    del_command = commands.add_parser("delete", help="Delete sensor groups")
    del_sensor_group_specifier = del_command.add_mutually_exclusive_group(required=True)
    del_sensor_group_specifier.add_argument("-i", "--id", type=int, help="ID of sensor group to delete")
    del_sensor_group_specifier.add_argument("-n", "--name",
                                            help="Name of sensor group to delete. Specify --force to delete"
                                            " multiple sensor groups that have the same name", dest="groupname")
    del_command.add_argument("--force",
                             help="If NAME matches multiple sensor groups, delete all matching sensor groups",
                             action="store_true", default=False)

    list_sensors_command = commands.add_parser("list-sensors", help="List all sensors in a sensor group")
    list_sensors_command.add_argument("-n", "--name", action="store", help="Sensor group name", required=False,
                                      dest="group_name")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    if args.command_name == "list":
        return list_sensor_groups(cb, parser, args)
    elif args.command_name == "add":
        return add_sensor_group(cb, parser, args)
    elif args.command_name == "delete":
        return delete_sensor_group(cb, parser, args)
    elif args.command_name == "list-sensors":
        return list_sensors(cb, parser, args)


if __name__ == "__main__":
    sys.exit(main())
