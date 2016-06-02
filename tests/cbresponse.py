import unittest

from nose.tools import assert_raises

from cbapi.response.models import Process, Binary, Sensor, Feed, Watchlist, Investigation, User
from cbapi.response.rest_api import CbEnterpriseResponseAPI

import requests_cache

class TestResponse(unittest.TestCase):
    def test_large_process_search(self):
        process = cb.select(Process).where('').first()

    def test_large_binary_search(self):
        binaries = cb.select(Binary).where('')
        print len(binaries)

    def test_sensor_search(self):
        sensor = cb.select(Sensor).first()

    def test_watchlist_search(self):
        watchlist = cb.select(Watchlist).first()

    def test_feed_search(self):
        feed = cb.select(Feed).first()

    def setUp(self):
        global cb
        cb = CbEnterpriseResponseAPI()
        requests_cache.install_cache(cache_file_name, allowable_methods=('GET', 'POST'), deny_outbound=True)


