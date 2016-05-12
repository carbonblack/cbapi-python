.. cbapi documentation master file, created by
   sphinx-quickstart on Thu Apr 28 09:52:29 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

cbapi: Carbon Black API for Python
==================================

Release v\ |version|.

cbapi provides a straightforward interface to the Carbon Black Enterprise Protection and Enterprise Response REST APIs.
This library provides a Pythonic layer to access the raw power of the REST APIs of both products, making it trivial
to do the easy stuff and handling all of the "sharp corners" behind the scenes for you. Take a look:

    >>> from cbapi.response import CbEnterpriseResponseAPI, Process, Binary, Sensor
    >>> c=CbEnterpriseResponseAPI()
    >>> # take the first process that ran notepad.exe, download the binary and read the first two bytes
    >>> c.select(Process).where('process_name:notepad.exe').first().binary.file.read(2)response import CbEnterpriseResponseAPI, Process, Binary, Sensor
    >>> c=CbEnterpriseResponseAPI()
    >>> # take the first process that ran notepad.exe, download the binary and read the first two bytes
    >>> c.select(Process).where('process_name:notepad.exe').first().binary.file.read(2)
    'MZ'
    >>> # if you want a specific ID, you can put it straight into the .select() call:
    >>> binary = c.select(Binary, "24DA05ADE2A978E199875DA0D859E7EB")
    >>> # isolate all sensors who ran notepad.exe
    >>> sensors = set()
    >>> for proc in c.select(Process).where('process_name:notepad.exe'):
    ...     sensors.add(proc.sensor)
    >>> for s in sensors:
    ...     s.network_isolation_enabled = True
    ...     s.save()

If you're more a Cb Enterprise Protection fellow, then you're in luck as well:

    >>> from cbapi.protection.models import FileInstance
    >>> from cbapi.ep.rest_api import CbEnterpriseProtectionAPI
    >>> p=CbEnterpriseProtectionAPI()
    >>> # Select the first file instance
    >>> fi = p.select(FileInstance).first()
    >>> # print that computer's hostname. This automatically "joins" with the Computer API object.
    >>> fi.computer.name
    u'DOMAIN\\MYHOSTNAME'
    >>> # change the policy ID
    >>> fi.computer.policyId = 3
    >>> fi.computer.save()



Major Features
--------------

- **Consistent API for both Cb Enterprise Response and Protection platforms**
    We now support Carbon Black Enterprise Response and Enterprise Protection users in the same API layer. Even better,
    the object model is the same for both; if you know one API you can easily transition to the other. cbapi
    hides all the differences between the two REST APIs behind a single, consistent Python-like interface.

- **Enhanced Performance**
    cbapi now provides a built in caching layer to reduce the query load on the Carbon Black server. This is especially
    useful when taking advantage of cbapi's new "joining" features. You can transparently access, for example, the
    binary associated with a given process in Carbon Black Enterprise Protection. Since many processes may be associated
    with the same binary, it does not make sense to repeatedly request the same binary information from the server
    over and over again. Therefore cbapi now caches this information to avoid unnecessary requests.

- **Reduce Complexity**
    cbapi now provides a friendly - dare I say "fun" - interface to the data. This greatly improves developer
    productivity and lowers the bar to entry.

- **Python 3 and Python 2 compatible**

- **Better support for multiple Cb servers**
    cbapi now introduces the concept of Credential Profiles; named collections of URL, API keys, and optional proxy
    configuration for connecting to any number of Carbon Black Enterprise Protection or Response servers.


Credentials
-----------

The new cbapi as of version 0.9.0 enforces the use of credential files.

Backwards Compatibility
-----------------------

The previous versions (0.8.x and earlier) of cbapi and bit9Api are now deprecated and will no longer receive updates.
However, existing scripts will work without change as cbapi includes both in its legacy package.
The legacy package is imported by default and placed in the top level cbapi namespace when the cbapi module
is imported on a Python 2.x interpreter. Therefore, scripts that expect to import cbapi.CbApi will continue to work
exactly as they had previously.

Since the old API was not compatible with Python 3, the legacy package is not importable in Python 3.x and therefore
legacy scripts cannot run under Python 3.

Once cbapi 2.0.0 is released, the old :py:mod:`cbapi.legacy.CbApi` will be deprecated and removed entirely no earlier than January 2017.
New scripts should use the :py:mod:`cbapi.CbEnterpriseResponseAPI` (for Carbon Black Enterprise Response) and
:py:mod:`cbapi.CbEnterpriseProtectionAPI` (for Carbon Black Enterprise Protection / former Bit9 Parity) API entry points.



Contents:

.. toctree::
   :maxdepth: 2

   enterprise-response



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

