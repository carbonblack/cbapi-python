import logging
from feed_helper import FeedHelper
from cabby import create_client
from cbapi.psc.threathunter import CbThreatHunterAPI, Report
from cbapi.errors import ApiError
from get_feed_ids import get_feed_ids
from cbapi.psc.threathunter.models import Feed

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)





class ThreatIntel:
    def __init__(self):
        self.cb = CbThreatHunterAPI()

    def input_validation(self, input):
        return

    def push_to_psc(self, feed_id, results):
        try:
            feed = self.cb.select(Feed, feed_id)
        except ApiError as e:
            log.error("couldn't find CbTH feed {0}: {1}".format(feed_id, e))
            return

        reports = []
        for result in results:
            rep_dict = {
                "id": str(result.analysis_name),
                "timestamp": int(result.scan_time.timestamp()),
                "title": str(result.title),
                "description": str(result.description),
                "severity": int(result.score),
                "iocs_v2": [ioc.as_dict() for ioc in result.iocs]
            }

            # report = self.cb.create(Report, rep_dict)
            report = Report(self.cb, initial_data=rep_dict, feed_id=feed_id)
            reports.append(report)

        feed.append_reports(reports)

    def get_feed_ids(self):
        get_feed_ids()
