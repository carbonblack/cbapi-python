#!/usr/bin/env python

import sys

from cbapi.errors import ObjectNotFoundError

from cbapi.response.models import Process
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
import csv
from six import PY3
from cbapi.response.models import CbChildProcEvent, CbFileModEvent, CbNetConnEvent, CbRegModEvent, CbModLoadEvent, CbCrossProcEvent


# UnicodeWriter class from http://python3porting.com/problems.html
class UnicodeWriter:
    def __init__(self, filename, dialect=csv.excel,
                 encoding="utf-8", **kw):
        self.filename = filename
        self.dialect = dialect
        self.encoding = encoding
        self.kw = kw

    def __enter__(self):
        if PY3:
            self.f = open(self.filename, 'wt',
                          encoding=self.encoding, newline='')
        else:
            self.f = open(self.filename, 'wb')
        self.writer = csv.writer(self.f, dialect=self.dialect,
                                 **self.kw)
        return self

    def __exit__(self, type, value, traceback):
        self.f.close()

    def writerow(self, row):
        if not PY3:
            row = [s.encode(self.encoding) for s in row]
        self.writer.writerow(row)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def event_summary(event):
    timestamp = str(event.timestamp)
    if type(event) == CbFileModEvent:
        return [event.parent.path, timestamp, event.type, event.path, '']
    elif type(event) == CbNetConnEvent:
        if event.domain:
            hostname = event.domain
        else:
            hostname = event.remote_ip
        hostname += ':%d' % event.remote_port

        return [event.parent.path, timestamp, event.direction + ' netconn', hostname, '']
    elif type(event) == CbRegModEvent:
        return [event.parent.path, timestamp, event.type, event.path, '']
    elif type(event) == CbChildProcEvent:
        try:
            childproc = event.process.cmdline
        except ObjectNotFoundError:
            childproc = "<unknown>"
        return [event.parent.path, timestamp, 'childproc', event.path, childproc]
    elif type(event) == CbModLoadEvent:
        return [event.parent.path, timestamp, 'modload', event.path, event.md5]
    elif type(event) == CbCrossProcEvent:
        return [event.source_path, timestamp, event.type, event.target_path, event.privileges]
    else:
        return None


def write_csv(proc, filename):
    total_events = 0
    written_events = 0

    with UnicodeWriter(filename) as eventwriter:
        eventwriter.writerow(['ProcessPath', 'Timestamp', 'Event', 'Path/IP/Domain', 'Comments'])
        for event in proc.all_events:
            total_events += 1
            summary = event_summary(event)
            if summary:
                written_events += 1
                eventwriter.writerow(summary)

    print("{0} events out of {1} total events exported from process at {2}".format(written_events, total_events,
                                                                                   proc.webui_link))


def main():
    parser = build_cli_parser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--processid", help="Process ID or URL to Process Analysis page")
    group.add_argument("--query", help="query to pull multiple processes")
    args = parser.parse_args()

    cb = get_cb_response_object(args)

    if args.processid:
        if args.processid.startswith("http"):
            # interpret as a URL
            proc = cb.from_ui(args.processid)
        else:
            # interpret as a Process ID
            proc = cb.select(Process, args.processid)

        write_csv(proc, "{0}.{1}.csv".format(proc.id,proc.segment))
    else:
        for proc in cb.select(Process).where(args.query):
            write_csv(proc, "{0}.{1}.csv".format(proc.id, proc.segment))


if __name__ == "__main__":
    sys.exit(main())
