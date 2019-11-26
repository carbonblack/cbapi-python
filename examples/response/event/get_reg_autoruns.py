#!/usr/bin/env python
#
# The MIT License (MIT)
#
# Copyright (c) 2015 Bit9 + Carbon Black
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from cbapi.event import on_event, registry
from cbapi.example_helpers import get_cb_response_object, build_cli_parser
import re
from cbapi.response import sensor_events, event
import sys
import time

autoruns = """\\registry\\machine\\system\\currentcontrolset\\control\\session manager\\bootexecute(.*)
\\registry\\machine\\system\\currentcontrolset\\services(.*)
\\registry\\machine\\system\\currentcontrolset\\services(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\runservicesonce(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\runservices(.*)
\\registry\\machine\\software\\microsoft\\windows nt\\currentversion\\winlogon\\notify(.*)
\\registry\\machine\\software\\microsoft\\windows nt\\currentversion\\winlogon\\userinit(.*)
\\registry\\machine\\software\\microsoft\\windows nt\\currentversion\\winlogon\\shell(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\shellserviceobjectdelayload(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\runonce(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\runonceex(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\run(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\policies\\explorer\\run(.*)
\\registry\\machine\\software\\microsoft\\windows nt\\currentversion\\windows(.*)
\\registry\\machine\\software\\microsoft\\windows\\currentversion\\explorer\\sharedtaskscheduler(.*)
\\registry\\machine\\software\\microsoft\\windows nt\\currentversion\\windows\\appinit_dlls(.*)
\\registry\\user\\(.*)\\software\\microsoft\\windows\\currentversion\\runservicesonce(.*)
\\registry\\user\\(.*)\\software\\microsoft\\windows\\currentversion\\runservices(.*)
\\registry\\user\\(.*)\\software\\microsoft\\windows nt\\currentversion\\winlogon\\shell(.*)
\\registry\\user\\(.*)\\software\\microsoft\\windows\\currentversion\\run(.*)
\\registry\\user\\(.*)\\software\\microsoft\\windows\\currentversion\\runonce(.*)
\\registry\\user\\(.*)\\software\\microsoft\\windows\\currentversion\\policies\\explorer\\run(.*)
\\registry\\user\\(.*)\\software\\microsoft\\windows nt\\currentversion\\windows\\load(.*)"""

autoruns_regex = re.compile("|".join(autoruns.replace("\\", "\\\\").split("\n")))


class GetRegistryValue(object):
    def __init__(self, registry_key):
        self.registry_key = registry_key

    def run(self, session):
        reg_info = session.get_registry_value(self.registry_key)
        return time.time(), session.sensor_id, self.registry_key, reg_info["value_data"]


@on_event("ingress.event.regmod")
def process_callback(cb, event_type, event_data):
    x = sensor_events.CbEventMsg()
    x.ParseFromString(event_data)

    regmod_path = str(x.regmod.utf8_regpath)

    if autoruns_regex.match(regmod_path):
        regmod_path = regmod_path.replace("\\registry\\machine\\", "HKLM\\")
        regmod_path = regmod_path.replace("\\registry\\user\\", "HKEY_USERS\\")
        regmod_path = regmod_path.strip()
        job = GetRegistryValue(regmod_path)
        registry_job = cb.live_response.submit_job(job.run, x.env.endpoint.SensorId)
        registry_job.add_done_callback(print_result)


def print_result(registry_job):
    try:
        timestamp, sensor_id, registry_key, registry_value = registry_job.result()
    except Exception:
        print("Error encountered when pulling registry key: {0}".format(registry_job.exception()))
    else:
        print("Got result for sensor ID {0} registry key {1}: value is {2}".format(sensor_id, registry_key,
                                                                                   registry_value))


def main():
    parser = build_cli_parser("Get value from any new regmods to autorun keys")
    args = parser.parse_args()
    cb = get_cb_response_object(args)

    # event_source = event.RabbitMQEventSource(cb)
    event_source = event.RabbitMQEventSource(cb)
    event_source.start()

    print("Listening on the event bus for regmods")

    # print_thread = ResultPrinter(cb)
    # print_thread.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        event_source.stop()
        print("Exiting event loop")

    print("Encountered the following exceptions during processing:")
    for error in registry.errors:
        print(error["exception"])


if __name__ == "__main__":
    sys.exit(main())
