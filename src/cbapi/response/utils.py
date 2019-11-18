#!/usr/bin/env python

import struct
from datetime import datetime, timedelta
import dateutil.parser
import socket
import codecs


cb_datetime_format = "%Y-%m-%d %H:%M:%S.%f"
# NOTE: solr_datetime_format changed in Cb 4.1 to include microseconds
solr_datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
sign_datetime_format = "%Y-%m-%dT%H:%M:%SZ"


"""Create a Cb 4.2-style GUID from components"""


def create_42_guid(sensor_id, proc_pid, proc_createtime):
    full_guid = codecs.encode(struct.pack('>IIQ', sensor_id, proc_pid, proc_createtime), "hex")
    return '%s-%s-%s-%s-%s' % (full_guid[:8], full_guid[8:12], full_guid[12:16],
                               full_guid[16:20], full_guid[20:])


def parse_42_guid(guid):
    guid_parts = guid.split('-')
    guid_int = codecs.decode("".join(guid_parts)[:32], "hex")
    return struct.unpack('>IIQ', guid_int)


def parse_process_guid(guid):
    sensor_id, proc_pid, proc_createtime = parse_42_guid(guid)
    return sensor_id, proc_pid, datetime(1601,1,1) + timedelta(microseconds=proc_createtime / 10)


def convert_to_solr(dt):
    return dt.strftime(solr_datetime_format)


def convert_from_solr(s):
    if s == -1:
        return dateutil.parser.parse("1970-01-01T00:00:00Z")

    return dateutil.parser.parse(s)


def convert_from_cb(s):
    # Use dateutil.parser to parse incoming dates; flexible on what we receive, strict on what we send.
    if s is None:
        return dateutil.parser.parse("1970-01-01T00:00:00Z")
    else:
        return dateutil.parser.parse(s)


def convert_event_time(s):
    # NOTE that this will strip incoming tzinfo data... right now we do this since incoming Cb event data is
    #  always relative to the local system clock on which it was created, and apparently sometimes the TZ data
    #  is included, and sometimes it isn't... so we normalize it by stripping off the TZ data (unfortunately)
    return convert_from_cb(s).replace(tzinfo=None)

def convert_to_cb(dt):
    return dt.strftime(cb_datetime_format)


def get_constants(prefix):
    """Create a dictionary mapping socket module constants to their names."""
    return dict((getattr(socket, n), n)
                for n in dir(socket)
                if n.startswith(prefix)
    )


protocols = get_constants("IPPROTO_")
