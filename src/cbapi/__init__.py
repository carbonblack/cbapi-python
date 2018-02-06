from __future__ import absolute_import
import cbapi.six

__title__ = 'cbapi'
__author__ = 'Carbon Black Developer Network'
__license__ = 'MIT'
__copyright__ = 'Copyright 2018 Carbon Black'
__version__ = '1.3.5'

# New API as of cbapi 0.9.0
from cbapi.response.rest_api import CbEnterpriseResponseAPI, CbResponseAPI
from cbapi.protection.rest_api import CbEnterpriseProtectionAPI, CbProtectionAPI
from cbapi.defense.rest_api import CbDefenseAPI

# LEGACY APIs, will deprecated as of cbapi 2.0.0
# only import these if the Python version is 2.x
if cbapi.six.PY2:
    from cbapi.legacy.cbapi import CbApi
    from cbapi.legacy import util
    from cbapi.legacy.bit9api import bit9Api
