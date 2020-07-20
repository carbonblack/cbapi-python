.. CBAPI documentation master file, created by
   sphinx-quickstart on Thu Apr 28 09:52:29 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

cbapi: Carbon Black API for Python
==================================

Release v\ |release|.

CBAPI provides a straightforward interface to the VMware Carbon Black products: Carbon Black EDR, Carbon Black App Control, and Carbon Black Cloud Endpoint Standard (formerly CB Response, CB Protection, and CB Defense).
This library provides a Pythonic layer to access the raw power of the REST APIs of all Carbon Black products, making it easier to query data from any platform or on-premise APIs, combine data from multiple API calls, manage all API credentials in one place, and manipulate data as Python objects. Take a look::

   >>> from cbapi.response import CbResponseAPI, Process, Binary, Sensor
   >>> #
   >>> # Create our CbAPI object
   >>> #
   >>> c = CbResponseAPI()
   >>> #
   >>> # take the first process that ran notepad.exe, download the binary and read the first two bytes
   >>> #
   >>> c.select(Process).where('process_name:notepad.exe').first().binary.file.read(2)
   'MZ'
   >>> #
   >>> # if you want a specific ID, you can put it straight into the .select() call:
   >>> #
   >>> binary = c.select(Binary, "24DA05ADE2A978E199875DA0D859E7EB")
   >>> #
   >>> # select all sensors that have ran notepad
   >>> #
   >>> sensors = set()
   >>> for proc in c.select(Process).where('process_name:evil.exe'):
   ...     sensors.add(proc.sensor)
   >>> #
   >>> # iterate over all sensors and isolate
   >>> #
   >>> for s in sensors:
   ...     s.network_isolation_enabled = True
   ...     s.save()

If you're a Carbon Black App Control customer (formerly CB Protection), you may use::

   >>> from cbapi.protection.models import FileInstance
   >>> from cbapi.protection import CbProtectionAPI
   >>> #
   >>> # Create our CB Protection API object
   >>> #
   >>> p = CbProtectionAPI()
   >>> #
   >>> # Select the first file instance
   >>> #
   >>> fi = p.select(FileInstance).first()
   >>> #
   >>> # print that computer's hostname. This automatically "joins" with the Computer API object.
   >>> #
   >>> fi.computer.name
   u'DOMAIN\\MYHOSTNAME'
   >>> #
   >>> # change the policy ID
   >>> #
   >>> fi.computer.policyId = 3
   >>> fi.computer.save()

As of version 1.2, CBAPI also supports Carbon Black Cloud Endpoint Standard (formerly CB Defense):

   >>> from cbapi.psc.defense import *
   >>> #
   >>> # Create our CB Defense API object
   >>> #
   >>> p = CbDefenseAPI()
   >>> #
   >>> # Select any devices that have the hostname WIN-IA9NQ1GN8OI and an internal IP address of 192.168.215.150
   >>> #
   >>> devices = c.select(Device).where('hostNameExact:WIN-IA9NQ1GN8OI').and_("ipAddress:192.168.215.150").first()
   >>> #
   >>> # Change those devices' policy into the Windows_Restrictive_Workstation policy.
   >>> #
   >>> for dev in devices:
   >>>     dev.policyName = "Restrictive_Windows_Workstation"
   >>>     dev.save()


Major Features
--------------

- **Enhanced Live Response API**
    The new CBAPI now provides a robust interface to the Carbon Black EDR Live Response capability.
    Easily create Live Response sessions, initiate commands on remote hosts, and pull down data as
    necessary to make your Incident Response process much more efficient and automated.

- **Consistent API across VMware Carbon Black platforms**
    CBAPI supports Carbon Black EDR, Carbon Black App Control, and Carbon Black Cloud Endpoint Standard customers from a single API layer. Even better,
    the object model is the same for all three, and if you know one API, you can easily transition to another. CBAPI
    manages the differences among the three REST APIs behind a single, consistent Python-like interface.

- **Enhanced Performance**
    CBAPI now provides a built in caching layer to reduce the query load on the Carbon Black server. This is especially
    useful when taking advantage of CBAPI's new "joining" features. You can transparently access, for example, the
    binary associated with a given process in Carbon Black EDR. Since many processes may be associated
    with the same binary, it does not make sense to repeatedly request the same binary information from the server
    over and over again. Therefore CBAPI now caches this information to avoid unnecessary requests.

- **Reduce Complexity**
    CBAPI provides a friendly interface for accessing Carbon Black data. This greatly improves developer
    productivity and lowers the bar to entry.

- **Python 3 and Python 2 compatible**
    Use all the new features and modules available in Python 3 with CBAPI. This module is compatible with Python
    versions 2.6.6 and above, 2.7.x, 3.4.x, and 3.5.x.

- **Better support for multiple CB servers**
    CBAPI introduces the concept of Credential Profiles; named collections of URL, API keys, and optional proxy
    configuration for connecting to any number of Carbon Black EDR, Carbon Black App Control, or Carbon Black Cloud Endpoint Standard servers.


API Credentials
---------------

CBAPI version 0.9.0 enforces the use of credential files. 

In order to perform any queries via the API, you will need to get the API token for your CB user. See the documentation
on the Developer Network website on how to acquire the API token for
`Carbon Black EDR (CB Response) <http://developer.carbonblack.com/reference/enterprise-response/authentication/>`_,
`Carbon Black App Control (CB Protection) <http://developer.carbonblack.com/reference/enterprise-protection/authentication/>`_, or
`Carbon Black Cloud Endpoint Standard (CB Defense) <http://developer.carbonblack.com/reference/cb-defense/authentication/>`_.

Once you acquire your API token, place it in one of the default credentials file locations:

* ``/etc/carbonblack/``
* ``~/.carbonblack/``
* ``/current_working_directory/.carbonblack/``

For distinction between credentials of different Carbon Black products, use the following naming convention for your credentials files:

* ``credentials.psc`` for Carbon Black Cloud Endpoint Standard, Audit & Remediation, and Enterprise EDR (CB Defense, CB LiveOps, and CB ThreatHunter)
* ``credentials.response`` for Carbon Black EDR (CB Response)
* ``credentials.protection`` for Carbon Black App Control (CB Protection)

For example, if you use a Carbon Black Cloud product, you should have created a credentials file in one of these locations:

* ``/etc/carbonblack/credentials.psc``
* ``~/.carbonblack/credentials.psc``
* ``/current_working_directory/.carbonblack/credentials.psc``

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

* **url**: The base URL of the Carbon Black server. This should include the protocol (https) and the hostname, and nothing else.
* **token**: The API token for the user ID. More than one credential profile can be specified for a given server, with
  different tokens for each.
* **ssl_verify**: True or False; controls whether the SSL/TLS certificate presented by the server is validated against
  the local trusted CA store.
* **org_key**: The organization key. This is required to access the Carbon Black Cloud, and can be found in the console. The format is ``123ABC45``.
* **proxy**: A proxy specification that will be used when connecting to the Carbon Black server. The format is:
  ``http://myusername:mypassword@proxy.company.com:8001/`` where the hostname of the proxy is ``proxy.company.com``, port
  8001, and using username/password ``myusername`` and ``mypassword`` respectively.
* **ignore_system_proxy**: If you have a system-wide proxy specified, setting this to True will force CBAPI to bypass
  the proxy and directly connect to the Carbon Black server.

Future versions of CBAPI will also provide the ability to "pin" the TLS certificate so as to provide certificate
verification on self-signed or internal CA signed certificates.

Environment Variable Support

The latest CBAPI for Python supports specifying API credentials in the following three environment variables:

`CBAPI_TOKEN` the envar for holding the CbR/CbP api token or the ConnectorId/APIKEY combination for Endpoint Standard (CB Defense)/Carbon Black Cloud.

The `CBAPI_URL` envar holds the FQDN of the target, a CbR , CBD, or CbD/Carbon Black Cloud server specified just as they are in the
configuration file format specified above.

The  optional `CBAPI_SSL_VERIFY` envar can be used to control SSL validation(True/False or 0/1), which will default to ON when
not explicitly set by the user.

Backwards & Forwards Compatibility
----------------------------------

The previous versions (0.8.x and earlier) of CBAPI and bit9Api are now deprecated and will no longer receive updates.
However, existing scripts will work without change as CBAPI includes both in its legacy package.
The legacy package is imported by default and placed in the top level CBAPI namespace when the CBAPI module
is imported on a Python 2.x interpreter. Therefore, scripts that expect to import cbapi.CbApi will continue to work
exactly as they had previously.

Since the old API was not compatible with Python 3, the legacy package is not importable in Python 3.x and therefore
legacy scripts cannot run under Python 3.

Once CBAPI 1.0.0 is released, the old :py:mod:`cbapi.legacy.CbApi` will be deprecated and removed entirely no earlier
than January 2017.
New scripts should use the :py:mod:`cbapi.response.rest_api.CbResponseAPI`
(for Carbon Black EDR, or CB Response), :py:mod:`cbapi.protection.rest_api.CbProtectionAPI`
(for Carbon Black App Control, or CB Protection), or :py:mod:`cbapi.defense.rest_api.CbDefenseAPI` API entry points.

The API is frozen as of version 1.0; any changes in the 1.x version branch
will be additions/bug fixes only. Breaking changes to the API will increment the major version number (2.x).

User Guide
----------

Get started with CBAPI here. For detailed information on the objects and methods exposed by CBAPI, see the full API Documentation below.

.. toctree::
   :maxdepth: 2

   installation
   getting-started
   concepts
   logging
   response-examples
   protection-examples
   live-response
   event-api
   changelog

API Documentation
-----------------

Once you have read the User Guide, you can view `examples on GitHub <https://github.com/carbonblack/cbapi-python/tree/master/examples>`_
or try writing code of your own. You can use the full API documentation below to see all the methods available in CBAPI 
and unlock the full functionality of the SDK.

.. toctree::
   :maxdepth: 2

   response-api
   protection-api
   defense-api
   threathunter-api
   psc-api
   livequery-api
   exceptions

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
