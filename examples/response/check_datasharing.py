#!/usr/bin/env python

import sys
from cbapi.response.models import SensorGroup
from cbapi.example_helpers import build_cli_parser, get_cb_response_object


def main():
    parser = build_cli_parser("Check datasharing settings on server")

    args = parser.parse_args()
    cb = get_cb_response_object(args)

    virustotal_groups = []
    for sg in cb.select(SensorGroup):
        settings = cb.get_object("/api/v1/group/{0}/datasharing".format(sg.id)) or []
        for setting in settings:
            if setting.get("what") == "BIN" and setting.get("who") == "VIRUSTOTAL":
                virustotal_groups.append(sg)

    if len(virustotal_groups) == 0:
        print("No sensor groups are configured to send unknown binaries to VirusTotal")
        return 0
    elif len(virustotal_groups) == len(cb.select(SensorGroup)):
        print("**ALL** sensor groups are configured to send unknown binaries to VirusTotal")
        return 1
    else:
        print("The following sensor groups are configured to send unknown binaries to VirusTotal:")
        for sg in virustotal_groups:
            print("  id {0}: {1}".format(sg.id, sg.name))
        return 1


if __name__ == "__main__":
    sys.exit(main())
