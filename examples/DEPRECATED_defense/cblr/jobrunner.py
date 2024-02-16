#!/usr/bin/env python

from cbapi.defense import Device
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object
from concurrent.futures import as_completed
import sys
from datetime import datetime, timedelta


def main():
    parser = build_cli_parser()
    parser.add_argument("--job", action="store", default="examplejob", required=True)

    args = parser.parse_args()

    cb = get_cb_defense_object(args)

    sensor_query = cb.select(Device)

    # Retrieve the list of sensors that are online
    # calculate based on sensors that have checked in during the last five minutes
    now = datetime.utcnow()
    delta = timedelta(minutes=5)

    online_sensors = []
    offline_sensors = []
    for sensor in sensor_query:
        if now - sensor.lastContact < delta:
            online_sensors.append(sensor)
        else:
            offline_sensors.append(sensor)

    print("The following sensors are offline and will not be queried:")
    for sensor in offline_sensors:
        print("  {0}: {1}".format(sensor.deviceId, sensor.name))

    print("The following sensors are online and WILL be queried:")
    for sensor in online_sensors:
        print("  {0}: {1}".format(sensor.deviceId, sensor.name))

    # import our job object from the jobfile
    job = __import__(args.job)
    jobobject = job.getjob()

    completed_sensors = []
    futures = {}

    # collect 'future' objects for all jobs
    for sensor in online_sensors:
        f = cb.live_response.submit_job(jobobject.run, sensor)
        futures[f] = sensor.deviceId

    # iterate over all the futures
    for f in as_completed(futures.keys(), timeout=100):
        if f.exception() is None:
            print("Sensor {0} had result:".format(futures[f]))
            print(f.result())
            completed_sensors.append(futures[f])
        else:
            print("Sensor {0} had error:".format(futures[f]))
            print(f.exception())

    still_to_do = set([s.deviceId for s in online_sensors]) - set(completed_sensors)
    print("The following sensors were attempted but not completed or errored out:")
    for sensor in still_to_do:
        print("  {0}".format(still_to_do))


if __name__ == '__main__':
    sys.exit(main())
