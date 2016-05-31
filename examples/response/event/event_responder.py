#!/usr/bin/env python

from cbapi.response import event
from cbapi.event import on_event, registry
from cbapi.example_helpers import get_cb_response_object, build_cli_parser
import sys
import time
import os


@on_event("event")
def event_callback(cb, event_type, event_data, **kwargs):
    print("Getting file from sensor")


def main():
    parser = build_cli_parser("Simple event listener. Calls a callback for every event received on the event bus")
    args = parser.parse_args()
    cb = get_cb_response_object(args)

    event_source = event.RabbitMQEventSource(cb)
    event_source.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        event_source.stop()
        print("Exiting event loop")

    print("Encountered the following exceptions during processing:")
    for error in registry.errors:
        print(error["traceback"])


if __name__ == "__main__":
    sys.exit(main())

