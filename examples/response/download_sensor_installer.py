#!/usr/bin/env python

import sys
from cbapi.response.models import SensorGroup
from cbapi.errors import ObjectNotFoundError
from cbapi.example_helpers import build_cli_parser, get_cb_response_object


def main():
    parser = build_cli_parser()
    parser.add_argument("--filename", "-f", action="store", default=None, dest="filename",
                        help="Filename to save the installer package to", required=True)
    parser.add_argument("--sensor-group", "-g", action="store", default="1", dest="group",
                        help="Sensor group name or ID of the group to download an installer for")
    parser.add_argument("--installer-type", "-t", action="store", default="windows/exe", dest="type",
                        help="Installer type; must be one of windows/exe, windows/msi, linux, osx")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    try:
        sensor_group_id = int(args.group)
        sensor_group = cb.select(SensorGroup, sensor_group_id, force_init=True)
    except (ValueError, ObjectNotFoundError):
        sensor_group = cb.select(SensorGroup).where('name:{0:s}'.format(args.group)).one()
    except Exception:
        print("Could not find sensor group via id or name ({0:s})".format(args.group))
        return 1

    # download the installer package
    #
    print("-> Downloading {0:s} installer for group {1:s} to file {2:s}...".format(args.type, sensor_group.name,
                                                                                   args.filename))
    try:
        open(args.filename, 'wb').write(sensor_group.get_installer(args.type))
    except ObjectNotFoundError:
        print("** Could not find an installer for {0:s}".format(args.type))
    except IOError:
        print("** Error writing to file {0:s}".format(args.filename))
    except Exception as e:
        print("** Unknown exception: {0:s}".format(str(e)))
    else:
        print("-> Download complete")


if __name__ == "__main__":
    sys.exit(main())
