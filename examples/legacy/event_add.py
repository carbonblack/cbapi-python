__author__ = 'bwolfson'

import sys
import optparse

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')

import cbapi

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Add a tagged_event to the server")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server_url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-i", "--investigation_id", action = "store", default = None, dest = "investigation_id",
                      help = "ID of investigation to add this event to")
    parser.add_option("-d", "--description", action = "store", default="", dest="description",
                      help="Description of the event, use quotes")
    parser.add_option("-s", "--start_date", action= "store", default = None, dest = "start_date",
                      help = "start date for the event")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.server_url or not opts.token or not opts.investigation_id or not opts.description or not opts.start_date:
      print "Missing required param; run with --help for usage"
      sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.server_url, token=opts.token, ssl_verify=opts.ssl_verify)

    event = cb.event_add(opts.investigation_id, opts.description, opts.start_date)
    print ""
    print "-->Event Added:"
    for key in event.keys():
            print "%-20s : %s" % (key, event[key])

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))