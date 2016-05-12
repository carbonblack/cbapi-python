import sys
import time
import struct
import socket
import pprint
import optparse 

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')

import cbapi 

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Display information about a particular feed report")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server_url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-i", "--id", action="store", default=None, dest="feedid",
                      help="Id of feed of which the specified report is a part of")
    parser.add_option("-r", "--reportid", action="store", default=None, dest="reportid",
                      help="Id of report to query; this may be alphanumeric")
    return parser

def get_ioc_counts(iocs):
    """
    returns counts of md5s, ipv4s, domains, and queries as a tuple given a feed report ioc block
    """
    return len(iocs.get('md5', [])), \
           len(iocs.get('ipv4', [])), \
           len(iocs.get('dns', [])), \
           len(iocs.get('query', []))

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.server_url or not opts.token or not opts.feedid or not opts.reportid:
      print "Missing required param; run with --help for usage"
      sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.server_url, token=opts.token, ssl_verify=opts.ssl_verify)

    # retrieve threat report 
    #
    report = cb.feed_report_info(opts.feedid, opts.reportid)

    # get ioc counts
    #
    count_md5s, count_ipv4s, count_domains, count_queries = get_ioc_counts(report.get('iocs', {}))

    # output the threat report details
    #
    print report["title"]
    print "-" * 80
    print

    print "  Report Summary"
    print "  %s" % ("-" * 78)
    print "  %-20s : %s" % ("Score", report["score"])
    print "  %-20s : %s" % ("Report Id", report["id"])
    print "  %-20s : %s" % ("Link", report["link"])
    print "  %-20s : %s" % ("Report Timestamp", time.strftime('%Y-%m-%d %H:%M:%S GMT', time.localtime(report["timestamp"]))) 
    print "  %-20s : %s" % ("Total IOC count", count_md5s + count_ipv4s + count_domains + count_queries)
    print

    print "  Feed Details"
    print "  %s" % ("-" * 78)
    print "  %-20s : %s" % ("Feed Name", report["feed_name"])
    print "  %-20s : %s" % ("Feed Id", report["feed_id"])
    print

    print "  Report IOCs"
    print "  %s" % ("-" * 78)
    print

    if count_md5s > 0:
        print "    MD5"
        print "    %s" % ("-" * 76)
        for md5 in report["iocs"]["md5"]:
            print "    %s" % md5
        print

    if count_ipv4s > 0:
        print "    IPv4"
        print "    %s" % ("-" * 76)
        for ipv4 in report["iocs"]["ipv4"]:
            print "    %s" % ipv4
        print

    if count_domains > 0:
        print "    Domain"
        print "    %s" % ("-" * 76)
        for domain in report["iocs"]["dns"]:
            print "    %s" % domain 
        print
    
    if count_queries > 0:
        print "    Query"
        print "    %s" % ("-" * 76)
        print "    %-18s : %s" % ("Query", report["iocs"]["query"][0]["search_query"])
        print "    %-18s : %s" % ("Index Type", report["iocs"]["query"][0]["index_type"])
        print

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
