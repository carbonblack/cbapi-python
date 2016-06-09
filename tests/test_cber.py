from cbapi.response.models import Binary, Process
from cbapi.response.rest_api import CbEnterpriseResponseAPI

from nose.tools import assert_equal
from testconfig import config

import requests_cache
import unittest
import os
import sys
import sqlite3

#import requests.packages.urllib3
#requests.packages.urllib3.disable_warnings()

#
# Golden Cache attributes for assertion tests
# TODO: move this to the sqlite golden cache file
#
if sys.version_info >= (3, 0):
    cache_file_name = os.path.join(os.path.dirname(__file__), "caches/cache.py3")
elif sys.version_info >= (2, 7):
    cache_file_name = os.path.join(os.path.dirname(__file__), "caches/cache.py27")
elif sys.version_info >= (2, 6):
    cache_file_name = os.path.join(os.path.dirname(__file__), "caches/cache.py26")
else:
    raise Exception("Unsupported python version")

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
    cur.execute('drop table if exists AssertionTest')
    cur.execute('create table AssertionTest (testname string primary key, testresult string)')
    con.commit()
    con.close()


#
# Install the cache
# NOTE: deny_outbound is set so we don't attempt comms and force using the cache
#
requests_cache.install_cache(cache_file_name, allowable_methods=('GET', 'POST'), deny_outbound=use_golden)


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
        global c

        if use_golden:
            #
            # We don't want to connect to a cbserver so using bogus values
            #
            c = CbEnterpriseResponseAPI(url="http://localhost", token="N/A", ssl_verify=False)
        else:
            c = CbEnterpriseResponseAPI()

    def test_all_binary(self):
        binary_query = c.select(Binary).where('')
        if use_golden:
            test_result = getTestResult('test_all_binary')[0]
            assert_equal(len(binary_query),
                         test_result,
                         "Number of Binaries returned should be {0}, but received {1}".format(
                             test_result, len(binary_query)))
        else:
            insertResult('test_all_binary', str(len(binary_query)))

    def test_read_binary(self):
        data = c.select(Binary).where('').first().file.read(2)
        if use_golden:
            assert_equal(data, b'MZ')

    def test_all_process(self):
        process_query = c.select(Process).where('')
        if use_golden:
            test_result = getTestResult('test_all_process')[0]
            assert_equal(len(process_query),
                         test_result,
                         "Number of Processes returned should be {0}, but received {1}".format(
                             test_result, len(process_query)))
        else:
            insertResult('test_all_process', str(len(process_query)))





