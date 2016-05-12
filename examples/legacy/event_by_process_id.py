__author__ = 'bwolfson'

import sys
import optparse

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')

import cbapi

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Get the info of the tagged_events for a certain investigation by process id")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server_url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-i", "--id", action = "store", default = None, dest = "id",
                      help = "process id of the event")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.server_url or not opts.token or not opts.id:
      print "Missing required param; run with --help for usage"
      sys.exit(-1)

    # build a cbapi object
    #

    cb = cbapi.CbApi(opts.server_url, token=opts.token, ssl_verify=opts.ssl_verify)

    event = cb.event_by_process_id(opts.id)
    for key in event.keys():
        print "%-20s : %s" % (key, event[key])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
