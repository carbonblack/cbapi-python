from __future__ import absolute_import
from cbapi.six import iteritems
import sys


def convert_query_params(qd):
    o = []
    for k, v in iteritems(qd):
        if type(v) == list:
            for item in v:
                o.append((k, item))
        else:
            o.append((k, v))

    return o


def calculate_elapsed_time_new(td):
    return td.total_seconds()


def calculate_elapsed_time_old(td):
    return float((td.microseconds +
                  (td.seconds + td.days * 24 * 3600) * 10**6)) / 10**6


if sys.version_info < (2, 7):
    calculate_elapsed_time = calculate_elapsed_time_old
else:
    calculate_elapsed_time = calculate_elapsed_time_new
