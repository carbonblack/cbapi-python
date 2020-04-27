"""Validates result dictionaries, creates ThreatHunter Reports, validates ThreatHunter Reports, and sends them to a ThreatHunter Feed.

Also allows for conversion from result dictionaries into ThreatHunter `Report` objects.
"""

import logging
import json
from cbapi.psc.threathunter import CbThreatHunterAPI, Report
from cbapi.errors import ApiError
from cbapi.psc.threathunter.models import Feed

log = logging.getLogger(__name__)

class ThreatIntel:
    def __init__(self):
        self.cb = CbThreatHunterAPI(timeout=200)

    def verify_feed_exists(self, feed_id):
        """Verify that a Feed exists"""
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

                if self.input_validation([report_dict]):
                    # create CB Report object
                    report = Report(self.cb, initial_data=report_dict, feed_id=feed_id)
                    report_list_to_send.append(report)
                    reports.append(report_dict)
                else:
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

    ##########################################################
    # Input validation of reports
    ##########################################################

    # Input validation for query IOC
    def query_ioc_validation(self, query_ioc):
        if isinstance(query_ioc, list):
            fields = ["search_query", "index_type"]
            field_data_types = [str, str]

            for query in query_ioc:
                status = [[fields[0], False], [fields[1], False]]

                status[0][1] = isinstance(query[fields[0]], field_data_types[0])
                status[1][1] = isinstance(query[fields[1]], field_data_types[1])

                if not status[0][1]:
                    log.warning(f"Missing Required Report Field: {str(status[0][0])}")

                if not status[1][1]:
                    log.warning(f"Field {str(status[1][0])} does not match correct data type")

            log.debug("Query IOC validation complete")
            return True
        else:
            log.warning("Query_ioc does not match correct data type")
            return False

    # Input validation for IOCs
    def ioc_validation(self, ioc):
        fields_opt = ["md5", "ipv4", "ipv6", "dns", "query"]
        fields_data_type = [str, str, str, str]

        ioc_fields = list(ioc.keys())
        status_opt = [[fields_opt[i], False] for i in range(len(fields_opt))]
        no_error = True

        # Iterate through ioc fields and check for validation
        for ioc_field in ioc_fields:
            if ioc_field in fields_opt and ioc[ioc_field]:
                if ioc_field == 'query':
                    query_ioc_status = self.query_ioc_validation(ioc[ioc_field])
                    no_error = no_error and query_ioc_status
                else:
                    index = fields_opt.index(ioc_field)
                    status_opt[index][1] = all(isinstance(elem, fields_data_type[index]) for elem in ioc[ioc_field])
                    no_error = no_error and status_opt[index][1]

                    if not status_opt[index][1]:
                        log.warning(f"Field {str(ioc_field)} does not match correct data type")
            else:
                log.warning(f"Invalid field: {str(ioc_field)}")
                no_error = no_error and False

        return no_error

    # Input validation for IOCsv2
    def iocv2_validation(self, iocv2):
        if not isinstance(iocv2, list):
            log.warning("IOCv2 must be a list of IOCv2 dictionaries")
            return False
        else:
            fields_req = ["id", "match_type", "values"]
            fields_opt = ["field", "link"]
            no_error = True

            for ioc_dictionary in iocv2:
                ioc_v2_fields = list(ioc_dictionary.keys())
                status_req = [[fields_req[i], False] for i in range(len(fields_req))]
                status_opt = [[fields_opt[i], False] for i in range(len(fields_opt))]

                for ioc_v2_field in ioc_v2_fields:
                    if ioc_v2_field in fields_req:
                        if not ioc_dictionary[ioc_v2_field]:
                            log.warning(f"Required field {str(ioc_v2_field)} is empty")
                            no_error = False
                        else:
                            if ioc_v2_field == 'values' and isinstance(ioc_dictionary[ioc_v2_field], list):
                                status_req[2][1] = all(isinstance(elem, str) for elem in ioc_dictionary[ioc_v2_field])
                                no_error = no_error and status_req[2][1]

                                if not status_req[2][1]:
                                    log.warning(f"Missing REQUIRED field or invalid data type: {str(ioc_v2_field)}")
                            else:
                                index = fields_req.index(ioc_v2_field)
                                status_req[index][1] = isinstance(ioc_dictionary[ioc_v2_field], str)
                                no_error = no_error and status_req[index][1]

                                if not status_req[index][1]:
                                    log.warning(f"Missing REQUIRED field or invalid data type: {str(ioc_v2_field)}")
                    elif ioc_v2_field in fields_opt:
                        if not ioc_dictionary[ioc_v2_field]:
                            log.warning(f"Optional field {str(ioc_v2_field)} is empty")
                        else:
                            iocv2_status = isinstance(ioc_dictionary[ioc_v2_field], str)
                            index = fields_opt.index(ioc_v2_field)
                            status_opt[index][1] = iocv2_status
                            no_error = no_error and iocv2_status

                            if not iocv2_status:
                                log.warning(f"Missing field or invalid data type: {str(ioc_v2_field)}")
                    else:
                        log.warning(f"Invalid field in IOCv2: {str(ioc_v2_field)}")
                        no_error = False

            return no_error

    # Input a list of dictionaries representing
    # reports to be checked and validated
    def input_validation(self, reports):
        if len(reports) < 1:
            log.debug("There are no reports to be validated")
        else:

            fields_req = ["id", "timestamp", "title", "description", "severity"]
            fields_opt = ["link", "tags", "iocs", "iocs_v2", "visibility"]

            # Iterate though the array and check for invalidation of each field
            for index, report in enumerate(reports):
                no_error = True
                status_req = [[fields_req[i], False] for i in range(len(fields_req))]
                status_opt = [[fields_opt[i], False] for i in range(len(fields_opt))]

                for key, val in report.items():
                    if key in fields_req:
                        if key == "timestamp" or key == "severity":
                            if isinstance(val, int):
                                idx = fields_req.index(key)
                                status_req[idx][1] = True
                                no_error = no_error and status_req[idx][1]
                            else:
                                log.warning(f"Missing REQUIRED field or invalid data type: {str(key)}")
                                no_error = no_error and False
                        else:
                            if isinstance(val, str):
                                idx = fields_req.index(key)
                                status_req[idx][1] = True
                                no_error = no_error and status_req[idx][1]
                            else:
                                log.warning(f"Missing REQUIRED field or invalid data type: {str(key)}")
                                no_error = no_error and False
                    elif key in fields_opt:
                        if key == "iocs":
                            ioc_status = self.ioc_validation(val)
                            status_opt[2][1] = ioc_status
                            no_error = no_error and ioc_status
                        elif key == "iocs_v2":
                            iocv2_status = self.iocv2_validation(val)
                            status_opt[3][1] = iocv2_status
                            no_error = no_error and iocv2_status
                        else:
                            if isinstance(val, str):
                                idx = fields_opt.index(key)
                                status_opt[idx][1] = True  # this is always true? What's the point
                                no_error = no_error and status_opt[idx][1]
                            else:
                                log.warning(f"Missing field or invalid data type: {str(key)}")
                    else:
                        log.warning(f"Invalid Report field: {str(key)}. Please remove from report before dispatching.")
                        no_error = no_error and False

                log.debug(f"Report {str(index)} validation complete")

            if no_error:
                log.debug("Report Validation found no errors in report schema")
            else:
                log.warning("Report Validation found an error in report schema")
                return False

            log.debug("Report Validation check complete")
            return True
