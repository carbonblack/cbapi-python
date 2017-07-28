#!/usr/bin/env python
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Carbon Black Inc.
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
#
#  last updated 2016-04-07 by Jason McFarland
#
from cbapi.response import CbResponseAPI
from cbapi.response.models import Process, Binary, Feed, Sensor, Watchlist
import unittest
from hoverpy import capture, simulate

@capture(tlsVerification=False,dbpath="cber-requests.db") 
def buildResponseCache():
    cb = CbResponseAPI(proxies={"https":"https://localhost:8500","http":"http://localhost:8500"})
    procs = cb.select(Process)
    print ("Process count = {}\n".format(len(procs)))
    binaries = cb.select(Binary)
    print ("Binary count = {}\n".format(len(binaries)))
    feeds = cb.select(Feed)
    print ("Feed count = {}\n".format(len(feeds)))
    sensors = cb.select(Sensor)
    print ("Sensor count = {}\n".format(len(sensors)))
    watchlists = cb.select(Watchlist)
    print ("Watchlist count = {}\n".format(len(watchlists)))

'''    
@simulate(tlsVerification=False,dbpath="cber-requests.db") 
def buildResponseCache():
    cb = CbResponseAPI(proxies={"https":"https://localhost:8500","http":"http://localhost:8500"})
    procs = cb.select(Process)
    print ("Process count = {}\n".format(len(procs)))
    binaries = cb.select(Binary)
    print ("Binary count = {}\n".format(len(binaries)))
    feeds = cb.select(Feed)
    print ("Feed count = {}\n".format(len(feeds)))
    sensors = cb.select(Sensor)
    print ("Sensor count = {}\n".format(len(sensors)))
    watchlists = cb.select(Watchlist)
    print ("Watchlist count = {}\n".format(len(watchlists)))
'''

def main():
    buildResponseCache()

if __name__=='__main__':
    main()


