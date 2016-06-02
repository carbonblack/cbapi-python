from cbapi.response.models import Binary, Process
from cbapi.response.rest_api import CbEnterpriseResponseAPI

from nose.tools import assert_equal
from testconfig import config

import os
import requests_cache
import unittest

#import requests.packages.urllib3
#requests.packages.urllib3.disable_warnings()

#
# Golden Cache attributes for assertion tests
# TODO: move this to the sqlite golden cache file
#
GOLDEN_CACHE_NAME = os.path.join(os.path.dirname(__file__), "caches/cache")
NUMBER_OF_BINARIES = 633
NUMBER_OF_PROCESSES = 1902

#
# Config file parsing
#
if config['cache']['use_golden'].lower() == "false":
    use_golden = False
else:
    use_golden = True

if use_golden:
    cache_file_name = GOLDEN_CACHE_NAME
else:
    cache_file_name = config['cache']['cache_filename']
    if config['cache']['cache_overwrite'].lower() == 'true':
        #
        # Delete old cache
        #
        os.remove(cache_file_name)

#
# Install the cache
# NOTE: deny_outbound is set so we don't attempt comms and force using the cache
#
print cache_file_name
requests_cache.install_cache(cache_file_name, allowable_methods=('GET', 'POST'), deny_outbound=True)


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
            assert_equal(len(binary_query),
                         NUMBER_OF_BINARIES,
                         "Number of Binaries returned should be %d, but received %d" % (
                         NUMBER_OF_BINARIES, len(binary_query)))
        else:
            #
            # TODO: Save to sqlite database
            #
            print len(binary_query)

    def test_read_binary(self):
        data = c.select(Binary).where('').first().file.read(2)
        if use_golden:
            assert_equal(data, "MZ")
        else:
            #
            # Save off the returned value into the database
            #
            pass

    def test_all_process(self):
        process_query = c.select(Process).where('')
        if use_golden:
            assert_equal(len(process_query),
                         NUMBER_OF_PROCESSES,
                         "Number of Processes returned should be %d, but received %d" % (
                         NUMBER_OF_PROCESSES, len(process_query)))
        else:
            # Save off the returned value into the database
            pass





