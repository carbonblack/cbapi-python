from cbapi.response.models import Binary, Process, Sensor, Watchlist, Feed
from cbapi.response.rest_api import CbResponseAPI

from nose.tools import assert_equal
from testconfig import config

import unittest
import os
import sys
import sqlite3

sys.path.append(os.path.dirname(__file__))
import requests_cache

cache_file_name = os.path.join(os.path.dirname(__file__), "caches/cber")
#
# Config file parsing
#
if config['cache']['use_golden'].lower() == "false":
    use_golden = False
else:
    use_golden = True

if not use_golden:
    if 'cache_file_name' in config['cache']:
        cache_file_name = config['cache']['cache_filename']
    if config['cache']['cache_overwrite'].lower() == 'true':
        overwrite = True
        #
        # Delete old cache
        #
        try:
            os.remove(cache_file_name + ".sqlite")
        except:
            pass

    #
    # Create our assertion table
    #
    con = sqlite3.connect(cache_file_name + ".sqlite")
    cur = con.cursor()
    cur.execute('DROP TABLE IF EXISTS AssertionTest')
    cur.execute('CREATE TABLE AssertionTest (testname string PRIMARY KEY, testresult string)')
    con.commit()
    con.close()


def insertResult(testname, testresult):
    con = sqlite3.connect(cache_file_name + ".sqlite")
    cur = con.cursor()
    cur.execute('insert into AssertionTest VALUES ("{0}", "{1}")'.format(testname, testresult))
    con.commit()
    con.close()


def getTestResult(testname):
    con = sqlite3.connect(cache_file_name + ".sqlite")
    cur = con.cursor()
    cur.execute('select testresult from AssertionTest where testname == "{0}"'.format(testname))
    result = cur.fetchone()
    con.close()
    return result


class TestCbResponse(unittest.TestCase):
    def setUp(self):
        requests_cache.install_cache(cache_file_name, allowable_methods=('GET', 'POST'), deny_outbound=use_golden,
                                     ignored_parameters=["active_only"])
        if use_golden:
            #
            # We don't want to connect to a cbserver so using bogus values
            #
            self.c = CbResponseAPI(url="https://localhost", token="N/A", ssl_verify=False)
        else:
            self.c = CbResponseAPI()

        self.sensor = self.c.select(Sensor, 1)
        self.lr_session = self.sensor.lr_session()

    def test_all_binary(self):
        binary_query = self.c.select(Binary).where('')
        if use_golden:
            test_result = getTestResult('test_all_binary')[0]
            assert_equal(len(binary_query),
                         test_result,
                         "Number of Binaries returned should be {0}, but received {1}".format(
                             test_result, len(binary_query)))
        else:
            insertResult('test_all_binary', str(len(binary_query)))

    def test_read_binary(self):
        data = self.c.select(Binary).where('').first().file.read(2)
        if use_golden:
            assert_equal(data, b'MZ')

    def test_all_process(self):
        process_query = self.c.select(Process).where('')
        if use_golden:
            test_result = getTestResult('test_all_process')[0]
            assert_equal(len(process_query),
                         test_result,
                         "Number of Processes returned should be {0}, but received {1}".format(
                             test_result, len(process_query)))
        else:
            insertResult('test_all_process', str(len(process_query)))

    def test_cblr_ps(self):
        processes = self.lr_session.list_processes()
        if use_golden:
            test_result = len(processes)
            assert_equal(len(processes),
                         test_result,
                         "Number of Binaries returned should be {0}, but received {1}".format(
                             test_result, len(processes)))
        else:
            insertResult('test_cblr_ps', str(len(processes)))

    def test_cblr_get(self):
        self.lr_session.get_raw_file(r"C:\test.txt")

    def test_cber_watchlists(self):
        watchlists = self.c.select(Watchlist)
        if use_golden:
            test_result = getTestResult('test_cber_watchlists')[0]
            assert_equal(len(watchlists),
                         test_result,
                         "Number of Watchlists returned should be {0}, but received {1}".format(
                             test_result, len(watchlists)))

        else:
            insertResult('test_cber_watchlists', str(len(watchlists)))

    def test_cber_feeds(self):
        feeds = self.c.select(Feed)

        if use_golden:
            test_result = getTestResult('test_cber_feeds')[0]
            assert_equal(len(feeds),
                         test_result,
                         "Number of Feeds returned should be {0}, but received {1}".format(
                             test_result, len(feeds)))
        else:
            insertResult('test_cber_feeds', str(len(feeds)))
