#!/usr/bin/python

from cbapi.six import iteritems
from cbapi.six.moves.configparser import RawConfigParser
from cbapi.protection import Connector, Notification, PendingAnalysis
from cbapi.example_helpers import get_cb_protection_object, build_cli_parser
import requests
import tempfile
import shutil
import datetime
import logging
import time
import sys

# logging
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


class VirusTotalConnector(object):
    def __init__(self, api, vt_token=None, connector_name='VirusTotal', allow_uploads=True, malicious_threshold=50,
                 potential_threshold=10):
        """VirusTotal connector main object.

        :param cbapi.protection.CbEnterpriseResponseAPI: api: API object
        :param str vt_token: API token provided by VirusTotal
        :param str connector_name: name of the connector. Defaults to 'VirusTotal'
        :param bool allow_uploads: True to allow uploads of binaries to the VirusTotal servers. If set to False,
            only hash lookups will be done to te virusTotal.
            Note: In case when allow_uploads is set to False  AND VirusTotal does not recognize the hash,
            associated Cb Protection file analysis request will be cancelled
        """

        if vt_token is None:
            raise TypeError("Missing required VT authentication token.")
        self.vt_token = vt_token
        self.vt_url = 'https://www.virustotal.com/vtapi/v2'
        self.polling_frequency = 30  # seconds

        self.malicious_threshold = malicious_threshold
        self.potential_threshold = potential_threshold

        # Global dictionary to track our VT scheduled scans. We need this since it takes VT a while to process results
        # and we don't want to keep polling VT too often
        # Any pending results will be kept here, together with next polling time
        self.awaiting_results = {}

        self.allow_uploads = allow_uploads

        self.connector = api.create(Connector, data={"name": connector_name, "analysisName": connector_name,
                                                     "connectorVersion": "1.0", "canAnalyze": True,
                                                     "analysisEnabled": True, "enabled": True})
        self.connector.save()

        log.info("Connector: {0:s}".format(str(self.connector)))

    def run(self):
        while True:
            for binary in self.connector.pendingAnalyses:
                self.process_request(binary)
            time.sleep(self.polling_frequency)

    def check_vt(self, resource_id):
        r = requests.get("{0:s}/file/report".format(self.vt_url),
                         params={"resource": resource_id, "apikey": self.vt_token})

        if r.status_code == 204:
            log.info("VirusTotal API rate limit reached, sleeping for 30 seconds")
            time.sleep(30)

        return r

    def process_response(self, binary, scanResults):
        if "positives" in scanResults:
            self.report_result(binary, scanResults)
        elif "scanId" in scanResults:
            self.schedule_check(binary, scanResults["scanId"])
        elif self.allow_uploads:
            self.upload_to_vt(binary)
            self.schedule_check(binary, binary.fileHash)
        else:
            binary.analysisStatus = PendingAnalysis.StatusCancelled
            log.info("%s: VirusTotal has no information and we aren't allowed to upload it. "
                     "Cancelling the analysis request." % binary.fileHash)
            binary.save()

    def report_result(self, binary, scanResults):
        # We have results. Create our notification
        n = binary.create_notification(data={"product": "VirusTotal", "malwareName": "", "malwareType": ""})

        # Let's see if it is malicious. Use some fancy heuristics...
        positivesPerc = 100 * scanResults.get('positives') / scanResults.get('total')
        if positivesPerc > self.malicious_threshold:
            n.analysisResult = Notification.ResultMalicious
            n.severity = "critical"
            n.type = "malicious_file"
        elif positivesPerc > self.potential_threshold:
            n.analysisResult = Notification.ResultPotentialThreat
            n.severity = "high"
            n.type = "potential_risk_file"
        else:
            n.analysisResult = Notification.ResultClean
            n.severity = "low"
            n.type = "clean_file"

        n.externalUrl = scanResults.get('permalink')

        # Enumerate scan results that have detected the issue and build our
        # 'malwareName' string for the notification
        scans = scanResults.get("scans", {})
        malware_type = [k + ":" + v["result"] for k, v in iteritems(scans) if v["detected"]]
        malware_name = [v["result"] for k, v in iteritems(scans) if v["detected"]]

        n.malwareType = "; ".join(malware_type[:4])
        n.malwareName = "; ".join(malware_name[:4])

        if len(malware_type) > 4:
            n.malwareName += "..."
            n.malwareType += "..."

        # Send notification
        n.save()

        if binary.fileHash in self.awaiting_results:
            del self.awaiting_results[binary.fileHash]

        log.info("VT analysis for %s completed. VT result is %d%% malware (%s). Reporting status: %s"
                 % (binary.fileHash, positivesPerc, n.malwareName, n.type))

    def upload_to_vt(self, binary):
        if binary.uploaded:
            log.info("%s: VirusTotal has no information on this hash. Uploading the file" % binary.fileHash)

            vt_upload_error = False

            with tempfile.NamedTemporaryFile() as outfp:
                shutil.copyfileobj(binary.file, outfp)
                outfp.seek(0)
                files = {'file': outfp}
                try:
                    r = requests.post(self.vt_url + "/file/scan", files=files, params={'apikey': self.vt_token})
                    if r.status_code != 200:
                        vt_upload_error = True
                except Exception:
                    log.exception("Could not send file %s to VirusTotal" % (binary.fileHash,))
                    vt_upload_error = True

            if vt_upload_error:
                binary.analysisStatus = PendingAnalysis.StatusError
                binary.analysisError = 'VirusTotal returned error when attempting to send file for scanning'
            else:
                binary.analysisStatus = PendingAnalysis.StatusSubmitted

            binary.save()
        else:
            log.info("%s: VirusTotal has no information on this hash. Waiting for agent to upload it."
                     % binary.fileHash)

    def schedule_check(self, binary, scanId):
        next_check = datetime.datetime.now() + datetime.timedelta(0, 3600)
        self.awaiting_results[binary.fileHash] = {'scanId': scanId, 'nextCheck': next_check}
        log.info("%s: Waiting for analysis to complete. Will check back after %s."
                 % (binary.fileHash, next_check.strftime("%Y-%m-%d %H:%M:%S")))

    def process_request(self, binary):
        if binary.fileHash in self.awaiting_results:
            lastAttempt = self.awaiting_results[binary.fileHash]
            if lastAttempt["nextCheck"] > datetime.datetime.now():
                return

            scanId = lastAttempt["scanId"]
            r = self.check_vt(scanId)
        else:
            r = self.check_vt(binary.fileHash)

        if r.status_code != 200:
            return

        scanResults = r.json()

        self.process_response(binary, scanResults)


def main():
    parser = build_cli_parser("VirusTotal Connector")
    parser.add_argument("--config", "-c", help="Path to configuration file", default="virustotal.ini")
    args = parser.parse_args()

    inifile = RawConfigParser({
        "vt_api_key": None,
        "retrieve_files": "true",
        "upload_binaries_to_vt": "false",
        "connector_name": "VirusTotal",
        "log_file": None,
    })
    inifile.read(args.config)

    config = {}
    config["vt_api_key"] = inifile.get("bridge", "vt_api_key")
    config["retrieve_files"] = inifile.getboolean("bridge", "retrieve_files")
    config["connector_name"] = inifile.get("bridge", "connector_name")
    config["upload_binaries_to_vt"] = inifile.getboolean("bridge", "upload_binaries_to_vt")

    log_file = inifile.get("bridge", "log_file")
    if log_file:
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(file_handler)

    if not config["vt_api_key"]:
        log.fatal("Cannot start without a valid VirusTotal API key, exiting")
        return 1

    log.info("Configuration:")
    for k, v in iteritems(config):
        log.info("    %-20s: %s" % (k, v))

    api = get_cb_protection_object(args)

    vt = VirusTotalConnector(
        api,
        vt_token=config["vt_api_key"],
        allow_uploads=config["upload_binaries_to_vt"],  # Allow VT connector to upload binary files to VirusTotal
        connector_name=config["connector_name"],
    )

    log.info("Starting VirusTotal processing loop")
    vt.run()


if __name__ == '__main__':
    sys.exit(main())
