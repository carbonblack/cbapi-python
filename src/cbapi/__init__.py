from __future__ import absolute_import
import cbapi.six as six

__title__ = 'cbapi'
__author__ = 'Carbon Black Developer Network'
__license__ = 'MIT'
__copyright__ = 'Copyright 2016 Carbon Black'
__version__ = '1.3.4'

# New API as of cbapi 0.9.0
from .response.rest_api import CbEnterpriseResponseAPI, CbResponseAPI
from .protection.rest_api import CbEnterpriseProtectionAPI, CbProtectionAPI
from .defense.rest_api import CbDefenseAPI

# LEGACY APIs, will deprecated as of cbapi 2.0.0
# only import these if the Python version is 2.x
if six.PY2:
    from .legacy.cbapi import CbApi
    from .legacy import util
    from .legacy.bit9api import bit9Api
