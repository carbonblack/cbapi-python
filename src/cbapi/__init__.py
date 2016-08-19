from __future__ import absolute_import
import six

__title__ = 'cbapi'
__author__ = 'Carbon Black Developer Network'
__license__ = 'MIT'
__copyright__ = 'Copyright 2016 Carbon Black'

try:
    __version__ = __import__('pkg_resources').get_distribution(__name__).version
except Exception:
    __version__ = 'dev'

# New API as of cbapi 0.9.0
from .response.rest_api import CbEnterpriseResponseAPI
from .protection.rest_api import CbEnterpriseProtectionAPI

# LEGACY APIs, will deprecated as of cbapi 2.0.0
# only import these if the Python version is 2.x
if six.PY2:
    from .legacy.cbapi import CbApi
    from .legacy import util
    from .legacy.bit9api import bit9Api
