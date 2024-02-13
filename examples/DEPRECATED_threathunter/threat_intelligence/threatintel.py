"""Validates result dictionaries, creates ThreatHunter Reports, validates ThreatHunter Reports, and sends them to a ThreatHunter Feed.

Also allows for conversion from result dictionaries into ThreatHunter `Report` objects.
"""

import logging
import json
from cbapi.psc.threathunter import CbThreatHunterAPI, Report
from cbapi.errors import ApiError
from cbapi.psc.threathunter.models import Feed
from schemas import ReportSchema
from schema import SchemaError

log = logging.getLogger(__name__)


class ThreatIntel:
    def __init__(self):
        self.cb = CbThreatHunterAPI(timeout=200)

    def verify_feed_exists(self, feed_id):
        """Verify that a Feed exists."""
        try:
            feed = self.cb.select(Feed, feed_id)
            return feed
        except ApiError:
            raise ApiError

    def push_to_cb(self, feed_id, results):
        feed = self.verify_feed_exists(feed_id)  # will raise an ApiError if the feed cannot be found
        if not feed:
            return
        report_list_to_send = []
        reports = []
        malformed_reports = []

        for result in results:
            try:
                report_dict = {
                    "id": str(result.id),
                    "timestamp": int(result.timestamp.timestamp()),
                    "title": str(result.title),
                    "description": str(result.description),
                    "severity": int(result.severity),
                    "iocs_v2": [ioc_v2.as_dict() for ioc_v2 in result.iocs_v2]
                }
                try:
                    ReportSchema.validate(report_dict)
                    # create CB Report object
                    report = Report(self.cb, initial_data=report_dict, feed_id=feed_id)
                    report_list_to_send.append(report)
                    reports.append(report_dict)
                except SchemaError as e:
                    log.warning("Report Validation failed. Saving report to file for reference.")
                    malformed_reports.append(report_dict)
            except Exception as e:
                log.error(f"Failed to create a report dictionary from result object. {e}")

        log.debug(f"Num Reports: {len(report_list_to_send)}")
        try:
            with open('reports.json', 'w') as f:
                json.dump(reports, f, indent=4)
        except Exception as e:
            log.error(f"Failed to write reports to file: {e}")

        log.debug("Sending results to Carbon Black Cloud.")

        if report_list_to_send:
            try:
                feed.append_reports(report_list_to_send)
                log.info(f"Appended {len(report_list_to_send)} reports to ThreatHunter Feed {feed_id}")
            except Exception as e:
                log.debug(f"Failed sending {len(report_list_to_send)} reports: {e}")

        if malformed_reports:
            log.warning("Some report(s) failed validation. See malformed_reports.json for reports that failed.")
            try:
                with open('malformed_reports.json', 'w') as f:
                    json.dump(malformed_reports, f, indent=4)
            except Exception as e:
                log.error(f"Failed to write malformed_reports to file: {e}")

