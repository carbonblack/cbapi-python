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
# -----------------------------------------------------------------------------
#
#  last updated 2016-10-03 by Jon Ross jross@carbonblack.com
#  2015-10-23 by Jason McFarland jmcfarland@bit9.com
#

from cbapi.response import event, BannedHash, Sensor
from cbapi.event import on_event, registry
from cbapi.example_helpers import get_cb_response_object, build_cli_parser
import sys
import time
import json
import shutil
from tempfile import NamedTemporaryFile
import sqlite3


def isolate_sensor(cb, sensor_id):
    sensor = cb.select(Sensor, sensor_id)
    sensor.network_isolation_enabled = True
    sensor.save()
    print("Successfully isolated sensor {} based on watchlist hit".format(sensor.hostname))


def blacklist_binary(cb, md5hash):
    bh = cb.create(BannedHash)
    bh.md5hash = md5hash
    bh.text = "Auto-Blacklist From Watchlist"
    bh.save()
    print("Successfully banned binary MD5sum {} based on watchlist hit".format(md5hash))


def perform_liveresponse(cb, sensor_id):
    sensor = cb.select(Sensor, sensor_id)
    with sensor.lr_session() as lr_session:
        running_processes = lr_session.list_processes()

        # get list of logged in users
        users = set([proc['username'].split('\\')[-1]
                     for proc in running_processes if proc['path'].find('explorer.exe') != -1])

        for user in users:
            print("10 Most Recent URLs visited in Chrome for user {0} on {1}:".format(user, sensor.hostname))

            with NamedTemporaryFile(delete=False) as tf:
                history_fp = lr_session.get_raw_file(
                    "c:\\users\\%s\\appdata\\local\\google\\chrome\\user data\\default\\history" % user)
                shutil.copyfileobj(history_fp, tf.file)
                tf.close()
                db = sqlite3.connect(tf.name)
                db.row_factory = sqlite3.Row
                cur = db.cursor()
                cur.execute(
                    "SELECT url, title, datetime(last_visit_time / 1000000 + (strftime('%s', '1601-01-01')), 'unixepoch') as last_visit_time FROM urls ORDER BY last_visit_time DESC")
                urls = [dict(u) for u in cur.fetchall()]

                for url in urls[:10]:
                    print(url["url"])

        print("")
        print("Services running on {0}:".format(sensor.hostname))

        running_services = lr_session.create_process("c:\\windows\\system32\\net.exe start")

        print(running_services)
        print("")


@on_event("watchlist.hit.binary")
def binary_callback(cb, event_type, event_data):
    parsed_json = json.loads(event_data)
    watchlist_name = parsed_json.get("watchlist_name", "")
    docs = parsed_json.get("docs", [])
    if type(docs) != list or len(docs) == 0:
        return

    if watchlist_name.startswith("ISOLATE:") or watchlist_name.startswith("LOCK:"):
        for item in docs:
            isolate_sensor(cb, item["sensor_id"])
    if watchlist_name.startswith("BAN:") or watchlist_name.startswith("LOCK:"):
        for item in docs:
            blacklist_binary(cb, item["md5"])


@on_event("watchlist.hit.process")
def process_callback(cb, event_type, event_data):
    parsed_json = json.loads(event_data)
    watchlist_name = parsed_json.get("watchlist_name", "")
    docs = parsed_json.get("docs", [])
    if type(docs) != list or len(docs) == 0:
        return

    if watchlist_name.startswith("ISOLATE:") or watchlist_name.startswith("LOCK:"):
        for item in docs:
            isolate_sensor(cb, item["sensor_id"])
    if watchlist_name.startswith("BAN:") or watchlist_name.startswith("LOCK:"):
        for item in docs:
            blacklist_binary(cb, item["process_md5"])
    if watchlist_name.startswith("LIVERESPONSE:"):
        # TODO: this is currently executed synchronously, blocking the receipt of further events until the
        # Live Response session is done... a proper solution would spawn a background thread to do the LR session.
        for item in docs:
            perform_liveresponse(cb, item["sensor_id"])


def main():
    parser = build_cli_parser("Event-driven example to BAN hashes, ISOLATE sensors, or LOCK (both ban & isolate) based on watchlist hits")
    args = parser.parse_args()
    cb = get_cb_response_object(args)

    # event_source = event.RabbitMQEventSource(cb)
    event_source = event.FileEventSource(cb, "/tmp/output.json")
    event_source.start()

    print("Listening on the event bus for watchlist hits")

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

