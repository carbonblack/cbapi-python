from cbapi.response.models import Process, Binary
from cbapi.errors import ObjectNotFoundError
import time
import pefile
from cbapi.example_helpers import build_cli_parser, disable_insecure_warnings, get_cb_response_object
import sys
import csv
from progressbar import ProgressBar, Bar, Percentage

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
    # Parse arguments
    #
    parser = build_cli_parser("System Check After Specified Date")
    parser.add_argument("-d", "--date-to-query", action="store", dest="date",
                        help="New since DATE, format YYYY-MM-DD")
    parser.add_argument("-f", "--output-file", action="store", dest="output_file",
                        help="output file in csv format")

    opts = parser.parse_args()
    if not opts.date:
        parser.print_usage()
        sys.exit(-1)

    #
    # Setup cbapi
    #
    cb = get_cb_response_object(opts)

    #
    # query for all processes that match our query
    #
    print("Performing Query...")
    query = "filewrite_md5:* last_update:[" + opts.date + "T00:00:00 TO *]"
    process_query = cb.select(Process).where(query)

    #
    # Create a set so we don't have duplicates
    #
    md5_list = set()

    #
    # Iterate through all the processs
    #
    for proc in process_query:
        #
        # Iterate through all the filemods
        #
        for fm in proc.filemods:
            #
            # if an md5 exists then save it to our set
            #
            if fm.md5:
                md5_list.add(fm.md5)

    #
    # Initialize Prgoress Bar
    #
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=len(md5_list)).start()

    #
    # CSV
    #
    if not opts.output_file:
        output_file = open("new_binaries_after_date.csv", 'wb')
    else:
        output_file = open(opts.output_file, 'wb')
    csv_writer = csv.writer(output_file)
    csv_writer.writerow(("Binary MD5", "Binary Link", "Signature Status", "Company",
                         "Observed Date", "Host Count", "Binary TimeStamp", "Number of Executions"))

    #
    # Iterate through our set
    #
    for i, md5 in enumerate(md5_list):

        pbar.update(i + 1)

        try:
            #
            # refresh our binary object with the CbER server
            # Note: this might cause an exception if the binary is not found
            #
            binary = cb.select(Binary, md5)
            if not binary:
                continue
            binary.refresh()

            #
            # Get the binary timestamp
            #
            binary_timestamp = time.asctime(time.gmtime(pefile.PE(data=binary.file.read()).FILE_HEADER.TimeDateStamp))
        except ObjectNotFoundError:
            pass
        else:

            #
            # Get the number of times executed by retrieving the number of search results
            #
            number_of_times_executed = len(cb.select(Process).where("process_md5:{0:s}".format(md5)))

            try:
                csv_writer.writerow((binary.md5,
                                     binary.webui_link,
                                     binary.signing_data.result if binary.signing_data.result else "UNSIGNED",
                                     binary.company_name,
                                     binary.server_added_timestamp,
                                     binary.host_count,
                                     binary_timestamp,
                                     number_of_times_executed))
            except Exception:
                print(binary)
    pbar.finish()


if __name__ == "__main__":
    sys.exit(main())
