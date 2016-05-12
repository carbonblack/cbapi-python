import sys
import time
import json
import struct
import socket
import pprint
import optparse 
import operator

# in the github repo, cbapi is not in the example directory
sys.path.append('../src/cbapi')

import cbapi 

thresholds = [1, 2, 4, 8, 32, 64, 128, 512, 1024]

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Output information sensor backlog state on a sensor-by-sensor basis")

    # for each supported output type, add an option
    #
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.url, token=opts.token, ssl_verify=opts.ssl_verify)

    # grab the global list of sensors
    # this includes backlog data for each sensor 
    # the backlog is measured in terms of bytes of binaries (store files) and event logs
    #
    sensors = cb.sensors()
    
    # create empty "buckets" of sensors based on thresholds of event backlog 
    #
    buckets = {}
    for threshold in thresholds:
        buckets[threshold] = []

    # update all the event backlog to be a numeric type for sorting
    #
    for sensor in sensors:
        sensor['num_eventlog_bytes'] = int(sensor.get('num_eventlog_bytes', 0))

    # sort by total event backlog (desc)
    #
    sensors.sort(key=operator.itemgetter('num_eventlog_bytes'))
    sensors.reverse()
 
    # output
    #
    print "%-30s | %-5s | %-50s | %-10s | %10s | %s" % ("Hostname", "Id", "SID", "BinBytes", "EventBytes", "EventMB") 
    print "%-30s | %-5s | %-50s | %-10s | %10s | %10s" % ('-' * 30, '-' * 5, '-' * 50, '-' * 10, '-' * 10, '-' * 10)
    for sensor in sensors:
       sid = sensor.get('computer_sid', '')
       if None is sid:
           sid = ""


       if True:
           print "%-30s | %-5s | %-50s | %-10s | %10s | %s" % (sensor.get('computer_name', ''),
                                                               sensor.get('id', ''),
                                                               sid,
                                                               sensor.get('num_storefiles_bytes', 0),
                                                               sensor.get('num_eventlog_bytes', 0),
                                                               sensor.get('num_eventlog_bytes', 0) / (1024 * 1024)
                                                         ) 

       for threshold in thresholds:
           if int(sensor.get('num_eventlog_bytes', 0)) < threshold * 1024 * 1024:
               buckets[threshold].append(sensor)
               break
 

    print
    print

    # output an overall summary of backlogs by 'buckets' of backlog
    # 
    bucketlist = buckets.keys()
    bucketlist.sort() 
    print "%-20s %s" % ("EventBacklogMB", "NumSensors")
    print "%-20s %s" % ("-" * 20, "-" * 20)
    for bucket in bucketlist:
       print "%-20s %s" % (bucket, len(buckets[bucket]))

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
