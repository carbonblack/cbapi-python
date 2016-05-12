from cbapi.util.cli_helpers import main_helper

from cbapi.legacy.util.live_response_helpers import LiveResponseHelper


def main(cb, args):
    filepath = args.get('filepath')
    sensor_id = int(args.get('sensorid'))
    lrh = LiveResponseHelper(cb, sensor_id)
    lrh.start()
    print "[*] Attempting to delete file: %s" % filepath
    results = lrh.del_file(filepath)
    print "\n[+] Results:\n============"
    for i in results:
        print i + ' = ' + str(results[i])
    lrh.stop()

if __name__ == "__main__":
    sensor_arg = ("-s", "--sensorid", "store", None, "sensorid", "Sensor id")
    file_arg = ("-f", "--filepath", "store", None, "filepath", "File Path")
    main_helper("Remove file from remote sensor", main, custom_required=[sensor_arg, file_arg])
