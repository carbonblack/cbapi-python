import enum
import logging
from datetime import datetime


class IOC():
    """
    Models an indicator of compromise detected during an analysis.

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
    """
    Models the result of an analysis performed by a connector.
    """

    def __init__(self, analysis_name, scan_time, score, title, description):
        self.connector_name = "STIX_TAXII"
        self.analysis_name = str(analysis_name)
        self.scan_time = scan_time
        self.score = score
        self.title = title
        self.description = description
        self.iocs = []

    def attach_ioc(self, *, match_type=IOC.MatchType.Equality, values, field, link):
        self.iocs.append(IOC(analysis=self.analysis_name, match_type=match_type, values=values, field=field, link=link))



    def normalize(self):
        """
        Normalizes this result to make it palatable for the CbTH backend.
        """
        if self.score <= 0 or self.score > 10:
            log.warning("normalizing OOB score: {}".format(self.score))
            self.score=max(1, min(self.score, 10))
            # NOTE: min 1 and not 0
            # else err 400 from cbapi: Report severity must be between 1 & 10
        return self

    def as_dict(self):
        return {"iocs": [ioc.as_dict() for ioc in self.iocs], **super().as_dict()}

    def as_dict_full(self):
        return {
            "id": self.analysis_name,
            "timestamp": self.scan_time,
            "title": self.title,
            "description": self.description,
            "severity": self.score,
            "iocs_v2": [ioc.as_dict() for ioc in self.iocs]
        }
