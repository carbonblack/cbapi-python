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

    def push_to_cb(self, feed_id, results):
        try:
            feed = self.cb.select(Feed, feed_id)
        except ApiError as e:
            log.error("couldn't find CbTH feed {0}: {1}".format(feed_id, e))
            return

        reports = []
        report_list_to_validate = []
        for result in results:
            rep_dict = {
                "id": str(result.analysis_name),
                "timestamp": int(result.scan_time.timestamp()),
                "title": str(result.title),
                "description": str(result.description),
                "severity": int(result.score),
                "iocs_v2": [ioc.as_dict() for ioc in result.iocs]
            }

            report_list_to_validate.append(rep_dict)

            # report = self.cb.create(Report, rep_dict)
            report = Report(self.cb, initial_data=rep_dict, feed_id=feed_id)
            reports.append(report)

        validation = self.input_validation(report_list_to_validate)
        if validation:
            log.debug("Sending results to Carbon Black Cloud.")
            feed.append_reports(reports)
        else:
            log.warning("Report Validation failed. Not sending results to Carbon Black Cloud.")

    def get_feed_ids(self):
        get_feed_ids()

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
            fields_req_data = [str, str, str]
            fields_opt_data = [str, str]
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
                            no_error = False
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

    # Customer will input a list of dictionaries representing
    # reports to be checked and validated
    def input_validation(self, reports):
        if len(reports) < 1:
            log.debug("There are no reports to be validated")
        else:

            fields_req = ["id", "timestamp", "title", "description", "severity"]
            fields_opt = ["link", "tags", "iocs", "iocs_v2", "visibility"]
            data_req = [str, int, str, str, int]
            data_opt = [str, str, str]

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
                                status_opt[idx][1] = True #this is always true? What's the point
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



    # mock_query_ioc = {
    #     "index_type": "abc",
    #     "search_query": "def"
    # }
    #
    # mock_ioc = {
    #     "md5": ["abc", "def"],
    #     "ipv4": ["hello", "world"],
    #     "ipv6": ["ghi", "jkl"],
    #     "dns": ["mno", "pqr"],
    #     "query": [{"index_type": "stu", "search_query": "vwx"}]
    # }
    #
    # mock_reports = [
    #     {
    #         "id": "ABC123",
    #         "timestamp": 1543424484422,
    #         "title": "Test Report 1",
    #         "description": "",
    #         "severity":5
    #     }
    # ]
    #
    # input_validation(mock_reports)
    # ioc_ret_status = ioc_validation(mock_ioc)
    # query_ret_status = query_ioc_validation(mock_query_ioc)
    #
