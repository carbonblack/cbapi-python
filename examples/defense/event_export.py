"""
Event Export Tool

usage: event_export.py [-h] [--appName APPNAME] startTime endTime fileName
"""

import requests
import argparse
import json
from datetime import datetime, timedelta


parser = argparse.ArgumentParser()
parser.add_argument("startTime", help="Start Time (2020-08-04T00:00:00.000Z)")
parser.add_argument("endTime", help="End Time (2020-08-05T00:00:00.000Z)")
parser.add_argument("fileName", help="The name of the json file ie. events.json")
parser.add_argument("--appName", "-a", help="The app name to limit events")
args = parser.parse_args()

with open(args.fileName, "a") as file:

    hostname = "!!REPLACE WITH HOSTNAME!!"

    url_with_app = '{}/integrationServices/v3/event?startTime={}&endTime={}&applicationName={}&rows=10000'
    url_without_app = '{}/integrationServices/v3/event?startTime={}&endTime={}&rows=10000'

    headers = {'x-auth-token': '!!REPLACE WITH API SECRET KEY!!/!!REPLACE WITH API ID!!'}  # key/id

    orig_end = datetime.strptime(args.endTime, '%Y-%m-%dT%H:%M:%S.%fZ')
    orig_start = datetime.strptime(args.startTime, '%Y-%m-%dT%H:%M:%S.%fZ')
    start = orig_end - timedelta(days=1)
    end = orig_end
    triggerEnd = False
    file.write('[')

    while True:
        print("Next End Event Time: {}".format(end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')))
        if start == orig_start:
            triggerEnd = True

        if args.appName:
            resp = requests.get(url_with_app.format(hostname,
                                                    start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                                    end.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                                    args.appName), headers=headers)
        else:
            resp = requests.get(url_without_app.format(hostname,
                                                       start.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                                       end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')), headers=headers)

        resp_json = resp.json()
        if resp_json["success"]:
            results = resp_json['results']

            end = datetime.fromtimestamp(((results[-1]["eventTime"] + 1) / 1000))
            start = end - timedelta(days=1)

            if start < orig_start:
                start = orig_start

            file.write(json.dumps(results)[1:-2])

            if resp_json["totalResults"] >= 10000:
                triggerEnd = False
            elif triggerEnd or end < start:
                print("Events have been exported")
                file.write(']')
                break
            file.write(',')

        else:
            breakpoint()
            print("API Call Failed!")
            print(resp.content)
            break
    file.close()
