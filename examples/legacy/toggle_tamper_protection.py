# REQUIREMENTS:
# pip install requests cbapi

import sys
import os
import argparse

from cbapi.legacy import bit9api

bit9 = bit9api.bit9Api(
	"https://server",  # Replace with actual Bit9 server URL
	token="XXXX",  # Replace with actual Bit9 user token from console
	ssl_verify=False  # Don't validate server's SSL certificate. Set to True unless using self-signed cert on IIS
)

# Main function for performing the search and toggling tamper protection
def main(argv):
	# Create the initial search_conditions list that will be populated
	search_conditions=['deleted:false']
	
	# Generate the parser object
	parser = argparse.ArgumentParser(description='This is a sample to search the API and disable tamper protection if it is enabled. All searches are done via a LIKE search')
	parser.add_argument('-n', action='store', dest='comp_name', help='Computer name to search for')
	parser.add_argument('-p', action='store', dest='policy', help='Policy name to search for')
	parser.add_argument('-u', action='store', dest='user_name', help='Last logged in user name to search for')
	parser.add_argument('-c', action='store', dest='connect_tf', help='Either true or false for connected computers', type=bool)
	parser.add_argument('-v', action='store', dest='version', help='Cb P Version to search for')
	parser.add_argument('-t', action='store_true', dest='test', help='Setting this flag will return which computers will be modified, but will not change the Tamper Protection setting')
	requiredNamed = parser.add_mutually_exclusive_group(required=True)
	requiredNamed.add_argument('--disableTP', dest='disableTP', action='store_true', help='Set this flag to DISABLE Tamper Protection on all found systems')
	requiredNamed.add_argument('--enableTP', dest='enableTP', action='store_true', help='Set this flag to ENABLE Tamper Protection on all found systems')
	
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
			parser.error("The '-c' argument MUST be equal to either 'true' or 'false'")
	if results.version != None:
		search_conditions.append('agentVersion:*'+results.version+'*')
	if results.enableTP:
		search_conditions.append('tamperProtectionActive:false')
	if results.disableTP:
		search_conditions.append('tamperProtectionActive:true')
	

	# Find all computers using the parameters provided at the command line
	comps = bit9.search('v1/computer?limit=0', search_conditions)
	if results.test:
		print("Running the script in test mode, no changes will be made")
		print("Number of systems that will be modified: %s" % len(comps))
		# For every found computer, print out the name, IP, and tamper protection status
		for c in comps: 
			print("Computer: %s (IP: %s)" % (c['name'], c['ipAddress']))
			print("Current Tamper Protection Status: %s" % (c['tamperProtectionActive']))
			print("--")
	else:
		# For every found computer, print out the name, IP, and tamper protection status
		for c in comps: 
			print("Computer: %s (IP: %s)" % (c['name'], c['ipAddress']))
			print("Current Tamper Protection Status: %s" % (c['tamperProtectionActive']))		
			# If the --enableTP flag was passed, do nothing if Tamper Protection is enabled, enable Tamper Protection if it is disabled
			if results.enableTP:
				if c['tamperProtectionActive'] is True:
					print("Tamper Protection is already enabled")
				if c['tamperProtectionActive'] is False:
					print("Enabling Tamper Protection...")
					bit9.update('v1/computer', c,'','newTamperProtectionActive=true')
			# If the --disableTP flag was passed, do nothing if Tamper Protection is disabled, disable Tamper Protection if it is enabled
			elif results.disableTP:
				if c['tamperProtectionActive'] is True:
					print("Disabling Tamper Protection...")
					bit9.update('v1/computer', c,'','newTamperProtectionActive=false')
				if c['tamperProtectionActive'] is False:
					print("Tamper Protection is already disabled")
			print("--")
if __name__ == "__main__":
	main(sys.argv[1:])
