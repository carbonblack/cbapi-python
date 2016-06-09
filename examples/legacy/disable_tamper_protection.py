import sys
import os
import argparse

# Includes the "common" folder that comes from GitHub
from cbapi.legacy import bit9api

bit9 = bit9api.bit9Api(
    "https://server",  # Replace with actual Bit9 server URL
    token="XXXX-XXXXX-XXXXX",  # Replace with actual Bit9 user token from console
    ssl_verify=False  # Don't validate server's SSL certificate. Set to True unless using self-signed cert on IIS
)

# This function will parse the command line used when running the script and perform the search
def main(argv):
    # Create the initial search_conditions list that will be populated. Only searches non-deleted systems
    search_conditions=['deleted:false']
    
    # Generate the parser object
    parser = argparse.ArgumentParser(description='This is a sample to search the API and and disable tamper protection on the computers that were found. All searches are done via a LIKE search')
    parser.add_argument('-n', action='store', dest='comp_name', help='Computer name to search for')
    parser.add_argument('-p', action='store', dest='policy', help='Policy name to search for')
    parser.add_argument('-u', action='store', dest='user_name', help='Last logged in user name to search for')
    parser.add_argument('-c', action='store', dest='connect_tf', help='Either true or false for connected computers')
    parser.add_argument('-v', action='store', dest='version', help='CbEP Version to search for')
    
    if argv == []:
        print("No arguments were provided")
        parser.print_help()
        sys.exit(1)
    
    # Store the results from the command line in the 'results' variable
    results = parser.parse_args()
    
    # Add the arguments into ths search_conditions list
    if results.comp_name != None:
        search_conditions.append('name:*'+results.comp_name+'*')
    if results.policy != None:
        search_conditions.append('policyName:*'+results.policy+'*')
    if results.user_name != None:
        search_conditions.append('users:*'+results.user_name+'*')
    if results.connect_tf != None:
        if results.connect_tf in ("true", "false"):
            search_conditions.append('connected:'+results.connect_tf)
        elif results.connect_tf not in ("true", "false"):
            print("Ignoring connected argument. It MUST be equal to either 'true' or 'false'")
    if results.version != None:
        search_conditions.append('agentVersion:*'+results.version+'*')

    # Find all computers using the parameters provided at the command line
    comps = bit9.search('v1/computer', search_conditions)
    
    # For every found computer, print out the name, IP, current tamper protection, and dusable tamper protection if it is enabled
    for c in comps: 
        print("Computer: %s (IP: %s)" % (c['name'], c['ipAddress']))
        print("Current Tamper Protection Status: %s" % (c['tamperProtectionActive']))
        if c['tamperProtectionActive'] is True:
            print("Disabling Tamper Protection...")
            bit9.update('v1/computer', c,'','newTamperProtectionActive=false')
            
if __name__ == "__main__":
    main(sys.argv[1:])
