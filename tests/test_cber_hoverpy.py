from cbapi.response.models import Binary, Process, Sensor, Watchlist, Feed
from cbapi.response.rest_api import CbResponseAPI
import unittest
from hoverpy import simulate

class CberTestSuite(unittest.TestCase):

    def setUp(self):
        self.cb = CbResponseAPI(proxies={"https":"https://localhost:8500","http":"http://localhost:8500"})

    @simulate(tlsVerification=False, dbpath="cber-requests.db")
    def test_process_search(self):
        procs = self.cb.select(Process)
        print ("Process count = {}\n".format(len(procs)))


    @simulate(tlsVerification=False, dbpath="cber-requests.db")
    def test_binary_search(self): 
        bins = self.cb.select(Binary)
        print ("Binaries count = {}\n".format(len(bins)))

    @simulate(tlsVerification=False, dbpath="cber-requests.db")
    def test_feed_search(self): 
        feeds = self.cb.select(Feed)
        print ("Feeds count = {}\n".format(len(feeds)))

    @simulate(tlsVerification=False, dbpath="cber-requests.db")
    def test_sensor_search(self): 
        sensors = self.cb.select(Sensor)
        print ("Sensors count = {}\n".format(len(sensors)))

    @simulate(tlsVerification=False, dbpath="cber-requests.db")
    def test_watchlist_search(self): 
        watchlists = self.cb.select(Watchlist)
        print ("Watchlists count = {}\n".format(len(watchlists)))

if __name__=="__main__":
    unittest.main()


