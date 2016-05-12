#!/usr/bin/env python

from cbapi.protection import Connector, PendingAnalysis, Notification
from cbapi.example_helpers import get_cb_protection_object, build_cli_parser
import logging
import time


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def process_request(api, i):
    # make sure we have the latest information
    i.refresh()

    log.info("Processing hash {0:s}".format(i.fileHash))

    if i.uploaded:
        log.info("I have a binary! let's download it")
        open(i.fileHash+".dat", "wb").write(i.file.read())

        # create a notification
        n = i.create_notification(data={"product": "EmptyAnalysis", "malwareName": "TEST MALWARE",
                                        "analysisResult": Notification.ResultMalicious, "severity": "high",
                                        "type": "whoa"})
        n.save()
    else:
        # wait till next time
        log.info("Waiting until hash {0:s} is uploaded".format(i.fileHash))


if __name__ == '__main__':
    parser = build_cli_parser("EmptyAnalysis: example connector for Carbon Black Enterprise Protection")
    args = parser.parse_args()

    api = get_cb_protection_object(args)
    vt_connector = api.create(Connector, data={"name": "EmptyAnalysis", "analysisName": "EmptyAnalysis",
                                               "connectorVersion": "1.0", "canAnalyze": True, "analysisEnabled": True,
                                               "enabled": True})
    vt_connector.save()

    connector_id = vt_connector.id
    log.info("Connector: {0:s}".format(str(vt_connector)))

    log.info("Starting processing loop")
    while True:
        for i in vt_connector.pendingAnalyses:
            process_request(api, i)
        time.sleep(10)

