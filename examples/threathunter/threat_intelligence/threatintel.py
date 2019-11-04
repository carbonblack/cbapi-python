import logging
from feed_helper import FeedHelper
from cabby import create_client
from cbapi.psc.threathunter import CbThreatHunterAPI, Report
from get_feed_ids import get_feed_ids
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

handled_exceptions = (NoURIProvidedError, ClientException)




get feed ids
push data
input validation ( make sure it's in PSC Report format)





class ThreatIntel:
    def __init__(self):
        self.cb = CbThreatHunterAPI()

    def input_validation(self, input):
        #Schema module? utils.py has it
        return

    def push_to_psc(self, feed_id, results):
        try:
            feed = self.cb.select(threathunter.Feed, feed_id)
        except ApiError as e:
            log.error(f"couldn't find CbTH feed {feed_id}: {e}")
            return

        reports = []
        for result in results:
            rep_dict = {
                "id": str(result.id),
                "timestamp": int(result.scan_time.timestamp()),
                "title": result.connector_name,
                "description": result.analysis_name,
                "severity": result.score,
                "iocs_v2": [ioc.as_dict() for ioc in result.iocs],
            }

            report = self.cb.create(Report, rep_dict)
            reports.append(report)

        feed.append_reports(reports)

    def get_feed_ids(self):
        get_feed_ids()
