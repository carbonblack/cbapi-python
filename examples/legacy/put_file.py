from cbapi.util.cli_helpers import main_helper

from cbapi.legacy.util.live_response_helpers import LiveResponseHelper


def main(cb, args):
    lfile = args.get('lfile')
    rfile = args.get('rfile')
    sensor_id = int(args.get('sensorid'))
    lrh = LiveResponseHelper(cb, sensor_id)
    lrh.start()
    
    print "[*] Attempting to upload file: %s" % lfile
    results = lrh.put_file(rfile, lfile)
    print "\n[+] Results:\n============"
    for i in results:
        print i + ' = ' + str(results[i])
    lrh.stop()

if __name__ == "__main__":
    sensor_arg = ("-s", "--sensorid", "store", None, "sensorid", "Sensor id")
    lfile_arg = ("-l", "--localfile", "store", None, "lfile", "Local File Path")
    rfile_arg = ("-r", "--remotefile", "store", None, "rfile", "Remote File Path")
    main_helper("Place a file on remote sensor", main, custom_required=[sensor_arg, lfile_arg, rfile_arg])
