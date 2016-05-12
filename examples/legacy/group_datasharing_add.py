__author__ = 'bwolfson'

import sys
import optparse

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')

import cbapi

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Add a new datasharing configuration for a sensor group in the server")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="server_url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-i", "--group_id", action="store", default=True, dest= "group_id",
                      help = "id of sensor group whose datasharing configs to enumerate")
    parser.add_option("-w", "--who", action="store", default=None, dest = "who",
                      help = "who to datashare with")
    parser.add_option("-d", "--what", action="store", default=None, dest = "what",
                      help = "what type of data to share")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.server_url or not opts.token or not opts.group_id or not opts.who or not opts.what:
      print "Missing required param; run with --help for usage"
      sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.server_url, token=opts.token, ssl_verify=opts.ssl_verify)


    #check if the given group_id truly corresponds to one of the existing sensor groups
    does_exist = False
    for group in cb.group_enum():
        if int(opts.group_id) == int(group['id']):
            does_exist = True

    if not does_exist:
        sys.exit(-1)

    #check if trying to add a configuration that already exists
    #also at this point opts.id is valid
    no_conflict = True
    curr_configs = cb.group_datasharing_enum(opts.group_id)
    for config in curr_configs:
        if opts.who.lower() == config['who'].lower() and \
           opts.what.lower() == config['what'].lower():
                no_conflict = False

    if no_conflict:
        datasharing_config = cb.group_datasharing_add(opts.group_id, opts.who, opts.what)
        for key in datasharing_config.keys():
            print "%-20s : %s" % (key, datasharing_config[key])
    else:
        print "configuration already exists"
        sys.exit(-1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))