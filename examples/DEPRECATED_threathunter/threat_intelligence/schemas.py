from schema import And, Or, Optional, Schema


IOCv2Schema = Schema(
    {
        "id": And(str, len),
        "match_type": And(str, lambda type: type in ["query", "equality", "regex"]),
        "values": And([str], len),
        Optional("field"): str,
        Optional("link"): str
    }
)

QueryIOCSchema = Schema(
    {
        "search_query": And(str, len),
        Optional("index_type"): And(str, len)
    }
)

IOCSchema = Schema(
    {
        Optional("md5"): And([str], len),
        Optional("ipv4"): And([str], len),
        Optional("ipv6"): And([str], len),
        Optional("dns"): And([str], len),
        Optional("query"): [QueryIOCSchema]
     }
)

ReportSchema = Schema(
    {
        "id": And(str, len),
        "timestamp": And(int, lambda n: n > 0),
        "title": And(str, len),
        "description": And(str, len),
        "severity": And(int, lambda n: n > 0 and n < 11),
        Optional("link"): str,
        Optional("tags"): [str],
        Optional("iocs_v2"): [IOCv2Schema],
        Optional("iocs"): IOCSchema,
        Optional("visibility"): str
    }
)
