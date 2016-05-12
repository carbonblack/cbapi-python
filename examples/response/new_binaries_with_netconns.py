from cbapi.response.models import Process, Binary
from cbapi.response import CbEnterpriseResponseAPI
import csv
import time
import pefile
import sys
from progressbar import ProgressBar, Bar, Percentage
from cbapi.example_helpers import build_cli_parser, disable_insecure_warnings

#
# requirements.txt
# pip install pefile
# pip install csv
# pip install progressbar
#


def main():

    #
    # Disable requests insecure warnings
    #
    disable_insecure_warnings()

    #
    # parse arguments
    #
    parser = build_cli_parser("New Binaries with Netconns")
    parser.add_argument("-d", "--date-to-query", action="store", dest="date",
                      help="New since DATE, format YYYY-MM-DD")
    parser.add_argument("-f", "--output-file", action="store", dest="output_file",
                        help="output file in csv format")

    opts = parser.parse_args()
    if not opts.date:
        parser.print_usage()
        sys.exit(-1)
    #
    # Initalize the cbapi-ng
    # TODO get_cb_object
    #
    cb = CbEnterpriseResponseAPI()

    #
    # Main Query
    #
    start_date = "[" + opts.date + "T00:00:00 TO *]"
    binary_query = cb.select(Binary).where(("host_count:[1 TO 3]"
                                            " server_added_timestamp:" + start_date +
                                            " -observed_filename:*.dll"
                                            " -digsig_publisher:Microsoft*"
                                            " -alliance_score_srstrust:*"))
    #
    # Setup the csv writer
    #
    if not opts.output_file:
        output_file = open("new_binaries_with_netconns.csv", 'wb')
    else:
        output_file = open(opts.output_file, 'wb')
    csv_writer = csv.writer(output_file)
    #
    # Write out CSV header
    #
    csv_writer.writerow(("FileName", "Hostname", "Username", "Network Connections",
                         "Process Link", "Binary Link", "Binary MD5", "Signature Status", "Company",
                         "Observed Date", "Host Count", "Binary TimeStamp"))

    #
    # Create Progress Bar
    #
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=len(binary_query)).start()

    for i, binary in enumerate(binary_query):

        #
        # Update progress bar
        #
        pbar.update(i + 1)

        #
        # Retrieve the binary timestamp
        #
        binary_timestamp = time.asctime(time.gmtime(pefile.PE(data=binary.file.read()).FILE_HEADER.TimeDateStamp))

        #
        # Build a sub query to see if this binary was executed and had netconns
        #
        sub_query = "process_md5:" + binary.md5 + " netconn_count:[1 TO *]"
        process_query = cb.select(Process).where(sub_query)

        #
        # Iterate through results
        #
        for process in process_query:

            #
            # Write out the result
            #
            csv_writer.writerow((process.path,
                                 process.hostname,
                                 process.username,
                                 process.netconn_count,
                                 process.webui_link,
                                 binary.webui_link,
                                 binary.md5,
                                 binary.digsig_result if binary.digsig_result else "UNSIGNED",
                                 binary.company_name,
                                 binary.server_added_timestamp,
                                 binary.host_count,
                                 binary_timestamp))
    pbar.finish()

if __name__ == "__main__":
    sys.exit(main())
