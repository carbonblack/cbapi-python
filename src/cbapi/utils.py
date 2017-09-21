from __future__ import absolute_import
from cbapi.six import iteritems
from cbapi.connection import CbAPISessionAdapter
import ssl


def convert_query_params(qd):
    o = []
    for k, v in iteritems(qd):
        if type(v) == list:
            for item in v:
                o.append((k, item))
        else:
            o.append((k, v))

    return o


def check_python_tls_compatibility():
    try:
        tls_adapter = CbAPISessionAdapter(force_tls_1_2=True)
    except Exception as e:
        ret = "TLSv1.1"

        if "OP_NO_TLSv1_1" not in ssl.__dict__:
            ret = "TLSv1.0"
        elif "OP_NO_TLSv1" not in ssl.__dict__:
            ret = "SSLv3"
        elif "OP_NO_SSLv3" not in ssl.__dict__:
            ret = "SSLv2"
        else:
            ret = "Unknown"
    else:
        ret = "TLSv1.2"

    return ret

