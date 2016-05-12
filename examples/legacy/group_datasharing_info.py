__author__ = 'bwolfson'

import sys
import optparse

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')

import cbapi

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Retrieve info of a specific datasharing configuration for a sensor group")

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
    parser.add_option("-d", "--config_id", action = "store", default=True, dest="config_id",
                      help = "id of specific configuration to delete")

    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.server_url or not opts.token or not opts.group_id or not opts.config_id:
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

    if does_exist:
        datasharing_config = cb.group_datasharing_info(opts.group_id, opts.config_id)

        for key in datasharing_config.keys():
            print "%-20s : %s" % (key, datasharing_config[key])
    else:
        sys.exit(-1)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))