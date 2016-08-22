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
    >>> from cbapi.protection import CbEnterpriseProtectionAPI
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


API Credentials
---------------

The new cbapi as of version 0.9.0 enforces the use of credential files.

In order to perform any queries via the API, you will need to get the API token for your Cb user. See the documentation
on the Developer Network website on how to acquire the API token for
`Enterprise Response <http://developer.carbonblack.com/reference/enterprise-response/authentication/>`_ or
`Enterprise Protection <http://developer.carbonblack.com/reference/enterprise-protection/authentication/>`_.

Once you acquire your API token, place it in one of the default credentials file locations:

* ``/etc/carbonblack/credentials.response`` (or ``.protection`` for Cb Enterprise Protection)
* ``~/.carbonblack/credentials.response``
* (current working directory) ``.carbonblack/credentials.response``

Credentials found in a later path will overwrite earlier ones.

The credentials are stored in INI format. The name of each credential profile is enclosed in square brackets, followed
by key-value pairs providing the necessary credential information::

    [default]
    url=https://localhost
    token=abcdef0123456789abcdef
    ssl_verify=False

    [prod]
    url=https://cbserver.prod.corp.com
    token=aaaaaa
    ssl_verify=True

    [otheruser]
    url=https://localhost
    token=bbbbbb
    ssl_verify=False

The possible options for each credential profile are:

* **url**: The base URL of the Cb server. This should include the protocol (https) and the hostname, and nothing else.
* **token**: The API token for the user ID. More than one credential profile can be specified for a given server, with
  different tokens for each.
* **ssl_verify**: True or False; controls whether the SSL/TLS certificate presented by the server is validated against
  the local trusted CA store.
* **proxy**: A proxy specification that will be used when connecting to the Cb server. The format is:
  ``http://myusername:mypassword@proxy.company.com:8001/`` where the hostname of the proxy is ``proxy.company.com``, port
  8001, and using username/password ``myusername`` and ``mypassword`` respectively.
* **ignore_system_proxy**: If you have a system-wide proxy specified, setting this to True will force cbapi to bypass
  the proxy and directly connect to the Cb server.

Future versions of cbapi will also provide the ability to "pin" the TLS certificate so as to provide certificate
verification on self-signed or internal CA signed certificates.

Backwards Compatibility
-----------------------

The previous versions (0.8.x and earlier) of cbapi and bit9Api are now deprecated and will no longer receive updates.
However, existing scripts will work without change as cbapi includes both in its legacy package.
The legacy package is imported by default and placed in the top level cbapi namespace when the cbapi module
is imported on a Python 2.x interpreter. Therefore, scripts that expect to import cbapi.CbApi will continue to work
exactly as they had previously.

Since the old API was not compatible with Python 3, the legacy package is not importable in Python 3.x and therefore
legacy scripts cannot run under Python 3.

Once cbapi 1.0.0 is released, the old :py:mod:`cbapi.legacy.CbApi` will be deprecated and removed entirely no earlier
than January 2017.
New scripts should use the :py:mod:`cbapi.response.rest_api.CbEnterpriseResponseAPI`
(for Carbon Black Enterprise Response) and :py:mod:`cbapi.protection.rest_api.CbEnterpriseProtectionAPI`
(for Carbon Black Enterprise Protection / former Bit9 Parity) API entry points.


Forwards Compatibility
----------------------

*The new API is still in development and may change subtly during the 0.9 release process.* Any breaking changes
will be documented in the changelog. The API will be frozen as of version 1.0; afterward, any changes in the 1.x version branch
will be additions/bug fixes only. Breaking changes to the API will increment the major version number (2.x).

Contents:

.. toctree::
   :maxdepth: 2

   enterprise-response
   enterprise-protection
   exceptions



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

