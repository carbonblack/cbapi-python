#!/usr/bin/env python
#
#The MIT License (MIT)
#
# Copyright (c) 2015 Bit9 + Carbon Black
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# -----------------------------------------------------------------------------

########
# DNS Exfiltration Search
# Usage: python cb-dns-exfil.py
# Author: Jon Ross (jross@bit9.com)
# Date: 17 Nov 2015
#
# This script applies Mark Baggett's freq tool avaialble at
# https://github.com/MarkBaggett/MarkBaggett/tree/master/freq to DNS searches
# found in Carbon Black made on the endpoint's command line.
#
# If the tool finds hostnames that appear to random or computer generated
# it will print a message with the hostname that made the lookup and the
# command line used to generate the query.  This is not an exact science
# but instead is meant to offer a means to find exfiltration via DNS
# after the fact or alert quickly if it occurs in your environment.  Results
# should be reviewed by an analyst before any actions are taken.
#
########
#### Replace these variables with the appropriate values for your environment.

CBADDR = "192.168.230.40"
API_TOKEN = "11f8e14d1d98469468b962f494885fbef9e16cc5"

#### The following variable is the query sent to Carbon Black.  By default
#### this script inspects all port 53 traffic but you could also filter out
#### your DNS servers by using the following
####
#### query = "ipport:53 -ipaddr:192.168.230.3 -ipaddr:192.168.230.6"
####
#### My DNS servers are 192.168.230.3 and 192.168.230.6.  Please adjust this
#### to match your server addresses.  You may safely remove or add an -ipaddr
#### directive if you have more or fewer servers in your environment.

query = "ipport:53"

#### The wordlist variable should point to your wordlist prepared for use
#### with freq.

wordlist = "englishwords.freq"

## Do not edit below this line unless you want to change the logic or output ##

import re
import cbapi
from freq import *
import requests

requests.packages.urllib3.disable_warnings()

myfreq = FreqCounter()
myfreq.load(wordlist)

cbURL = "https://"+CBADDR

c = cbapi.CbApi(cbURL, ssl_verify=False, token=API_TOKEN)

for results in c.process_search_iter(query):
    if results['cmdline']:
        a = re.search('\s(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*\.?\s', results['cmdline'])
        if a:
            fqdn = a.group(0)
            parts=fqdn.split('.')
            score = myfreq.probability(parts[0])
            if score<5:
                print 'Possible DNS exfil from host %s using %s' % (results['hostname'],results['cmdline'])
