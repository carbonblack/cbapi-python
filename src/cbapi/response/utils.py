#!/usr/bin/env python

import struct
from datetime import datetime
import socket


cb_datetime_format = "%Y-%m-%d %H:%M:%S.%f"
# NOTE: solr_datetime_format changed in Cb 4.1 to include microseconds
solr_datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
sign_datetime_format = "%Y-%m-%dT%H:%M:%SZ"


"""Create a Cb 4.2-style GUID from components"""


# TODO: Py3 Compatibility (encode/decode hex)
def create_42_guid(sensor_id, proc_pid, proc_createtime):
    full_guid = struct.pack('>IIQ', sensor_id, proc_pid, proc_createtime).encode('hex')
    return '%s-%s-%s-%s-%s' % (full_guid[:8], full_guid[8:12], full_guid[12:16],
                               full_guid[16:20], full_guid[20:])


# TODO: Py3 Compatibility (encode/decode hex)
def parse_42_guid(guid):
    guid_parts = guid.split('-')
    return struct.unpack('>IIQ', ''.join(guid_parts)[:32].decode('hex'))


def convert_to_solr(dt):
    return dt.strftime(solr_datetime_format)


# TODO: change these to use dateutil.parser (see http://labix.org/python-dateutil)
def convert_from_solr(s):
    if s == -1:
        # special case for invalid processes
        return datetime.fromtimestamp(0)

    try:
        return datetime.strptime(s, solr_datetime_format)
    except ValueError:
        # try interpreting the timestamp without the milliseconds
        return datetime.strptime(s, sign_datetime_format)


def convert_from_cb(s):
    # hack: we strip off the timezone if it exists
    # by simply cutting off the string by 26 characters
    # 2014-06-03 10:14:14.637964

    if not s or s == -1:
        # special case for invalid processes
        return datetime.fromtimestamp(0)

    s = s[:26]
    return datetime.strptime(s, cb_datetime_format)


def convert_to_cb(dt):
    return dt.strftime(cb_datetime_format)


def get_constants(prefix):
    """Create a dictionary mapping socket module constants to their names."""
    return dict((getattr(socket, n), n)
                for n in dir(socket)
                if n.startswith(prefix)
    )


protocols = get_constants("IPPROTO_")
