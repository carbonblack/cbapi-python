from __future__ import absolute_import
from six import iteritems


def convert_query_params(qd):
    o = []
    for k, v in iteritems(qd):
        if type(v) == list:
            for item in v:
                o.append((k, item))
        else:
            o.append((k, v))

    return o


