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

from cbapi.response import event, BannedHash
from cbapi.event import on_event, registry
from cbapi.example_helpers import get_cb_response_object, build_cli_parser
import sys
import time
import os
import json


@on_event("watchlist.hit.binary")
@on_event("watchlist.hit.process")
def watchlist_callback(cb, event_type, event_data):
    print("Received event type: {0} with data length {1} (from cb server {2})".format(event_type, len(event_data),
          cb.url))
    event_data = json.loads(event_data)

    bh = cb.create(BannedHash)
    bh.md5hash = event_data["docs"][0]["process_md5"]
    bh.text = "banned via automated process!"
    bh.save()


def main():
    parser = build_cli_parser("Event-driven example to BAN hashes, ISOLATE sensors, or LOCK (both ban & isolate) based on watchlist hits")
    args = parser.parse_args()
    cb = get_cb_response_object(args)

    event_source = event.FileEventSource(cb, "/tmp/output.json")
    event_source.start()

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

