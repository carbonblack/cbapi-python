__author__ = 'bwolfson'


import sys
import optparse

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')

import cbapi

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Delete a certain action of a specified feed from the server")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server_url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-i", "--id", action = "store", default = None, dest = "id",
                      help = "id of the feed")
    parser.add_option("-d", "--action_id", action = "store", default = None, dest = "action_id",
                      help = "id of the action to be deleted")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.server_url or not opts.token or not opts.id or not opts.action_id:
      print "Missing required param; run with --help for usage"
      sys.exit(-1)

    # build a cbapi object
    #

    cb = cbapi.CbApi(opts.server_url, token=opts.token, ssl_verify=opts.ssl_verify)

    result = cb.feed_action_del(opts.id, opts.action_id)
    print result

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))