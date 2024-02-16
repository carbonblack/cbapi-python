#!/usr/bin/env python3

# Carbon Black Cloud -Dell Bios Verification LiveResponse
# Copyright VMware 2020
# May 2020
# Version 0.1
# pdrapeau [at] vmware . com
#
# usage: BiosVerification.py [-h] [-m MACHINENAME] [-g] [-o ORGPROFILE]
# 
# optional arguments:
#   -h, --help            show this help message and exit
#   -m MACHINENAME, --machinename MACHINENAME
#                         machinename to run host bios forensics on
#   -g, --get           Get BIOS images
#
#   -o ORGPROFILE, --orgprofile ORGPROFILE
#                         Select your cbapi credential profile

import os, sys, time, argparse
from cbapi.defense import *

def live_response(cb, host=None, response=None):
    
    print ("")

    #Select the device you want to gather forensic data from
    query_hostname = "hostNameExact:%s" % host
    print ("[ * ] Establishing LiveResponse Session with Remote Host:")

    #Create a new device object to launch LR on
    device = cb.select(Device).where(query_hostname).first()
    print("     - Hostname: {}".format(device.name))
    print("     - OS Version: {}".format(device.osVersion))
    print("     - Sensor Version: {}".format(device.sensorVersion))
    print("     - AntiVirus Status: {}".format(device.avStatus))
    print("     - Internal IP Address: {}".format(device.lastInternalIpAddress))
    print("     - External IP Address: {}".format(device.lastExternalIpAddress))
    print ("")

    #Execute our LR session
    with device.lr_session() as lr_session:
        print ("[ * ] Uploading scripts to the remote host")
        lr_session.put_file(open("dellbios.bat", "rb"), "C:\\Program Files\\Confer\\temp\\dellbios.bat")

        if response == "get":
            print ("[ * ] Getting the images")
            result = lr_session.create_process("cmd.exe /c .\\dellbios.bat", wait_for_output=True, remote_output_file_name=None, working_directory="C:\\Program Files\\Confer\\temp\\", wait_timeout=120, wait_for_completion=True).decode("utf-8")
            print ("")
            print("{}".format(result))
            
            print ("[ * ] Removing scripts")
            lr_session.create_process("powershell.exe del .\\dellbios.bat", wait_for_output=False, remote_output_file_name=None, working_directory="C:\\Program Files\\Confer\\temp\\", wait_timeout=30, wait_for_completion=False)

            
            print ("[ * ] Downloading images")
            zipdata = lr_session.get_file("C:\\Program Files\\Confer\\temp\\BiosImages.zip")
            
            print ("[ * ] Writing out " + host + "-BiosImages.zip")
            zipfile = open(host + "-BiosImages.zip","wb")
            zipfile.write(zipdata)
            
            print ("")
            

            
        else:
            print ("[ * ] Nothing to do")
            

        print ("[ * ] Cleaning up")
        lr_session.create_process("powershell.exe del .\\BiosImages.zip", wait_for_output=False, remote_output_file_name=None, working_directory="C:\\Program Files\\Confer\\temp\\", wait_timeout=30, wait_for_completion=False)
        lr_session.create_process("powershell.exe del C:\\tmpbios\\*.*", wait_for_output=False, remote_output_file_name=None, working_directory="C:\\Program Files\\Confer\\temp\\", wait_timeout=30, wait_for_completion=False)


        print ("")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--machinename", help = "machinename to run host forensics recon on")
    parser.add_argument("-g", "--get", help = "Get the Dell BIOS Verification images", action = "store_true")
    parser.add_argument('-o', '--orgprofile', help = "Select your cbapi credential profile", dest = "orgprofile", default = "default")
    args = parser.parse_args()

    #Create the CbD LR API object
    cb = CbDefenseAPI(profile="{}".format(args.orgprofile))

    if args.machinename:
        if args.get:
            live_response(cb, host=args.machinename, response="get")
        else:
            print ("Nothing to do...")
    else:
        print ("[ ! ] You must specify a machinename with a --machinename parameter. IE ./BiosVerification.py --machinename cheese")

if __name__ == "__main__":
  main()