import enum
import logging


class IOC_v2():
    """Models an indicator of compromise detected during an analysis.

    Every IOC belongs to an AnalysisResult.
    """

    def __init__(self, analysis, match_type, values, field, link):
        self.id = analysis
        self.match_type = match_type
        self.values = values
        self.field = field
        self.link = link

    class MatchType(str, enum.Enum):
        """
        Represents the valid matching strategies for an IOC.
        """

        Equality: str = "equality"
        Regex: str = "regex"
        Query: str = "query"

    def as_dict(self):
        return {
            "id": str(self.id),
            "match_type": self.match_type,
            "values": list(self.values),
            "field": self.field,
            "link": self.link,
        }


class AnalysisResult():
    """Models the result of an analysis performed by a connector."""

    def __init__(self, analysis_name, scan_time, score, title, description):
        self.id = str(analysis_name)
        self.timestamp = scan_time
        self.title = title
        self.description = description
        self.severity = score
        self.iocs = []
        self.iocs_v2 = []
        self.link = None
        self.tags = None
        self.visibility = None
        self.connector_name = "STIX_TAXII"

    def attach_ioc_v2(self, *, match_type=IOC_v2.MatchType.Equality, values, field, link):
        self.iocs_v2.append(IOC_v2(analysis=self.id, match_type=match_type, values=values, field=field, link=link))

    def normalize(self):
        """Normalizes this result to make it palatable for the CbTH backend."""

        if self.severity <= 0 or self.severity > 10:
            logging.warning("normalizing OOB score: {}".format(self.severity))
            if self.severity > 10 and self.severity < 100:
                #assume it's a percentage
                self.severity = round(self.severity/10)
            else:
                # any severity above 10 becomes 10, or below 1 becomes 1
                # Report severity must be between 1 & 10, else CBAPI throws 400 error
                self.severity = max(1, min(self.severity, 10))
        return self

    def as_dict(self):
        return {"IOCs_v2": [ioc_v2.as_dict() for ioc_v2 in self.iocs_v2], **super().as_dict()}

    def as_dict_full(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "iocs_v2": [iocv2.as_dict() for iocv2 in self.iocs_v2]
        }
