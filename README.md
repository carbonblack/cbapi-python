# Python bindings for Carbon Black REST API

**Latest Version: 1.4.0**

[![Build Status](https://travis-ci.org/carbonblack/cbapi-python.svg?branch=master)](https://travis-ci.org/carbonblack/cbapi-python)

These are the new Python bindings for the Carbon Black Enterprise Response and Enterprise Protection REST APIs.
To learn more about the REST APIs, visit the Carbon Black Developer Network Website at https://developer.carbonblack.com.

Please visit https://cbapi.readthedocs.io for detailed documentation on this API. Additionally, we have a slideshow
available at https://developer.carbonblack.com/2016/07/presentation-on-the-new-carbon-black-python-api/ that provides
an overview of the concepts that underly this API binding.

## Support

If you have questions on the Carbon Black API or these API Bindings, please contact us at dev-support@carbonblack.com.
Also review the documentation and guides available on the 
[Carbon Black Developer Network website](https://developer.carbonblack.com)

## Requirements

The new cbapi is designed to work on Python 2.6.6 and above (including 3.x). If you're just starting out,
we recommend using the latest version of Python 3.6.x or above.

All requirements are installed as part of `pip install`. 
The legacy cbapi (`cbapi.CbApi`) and legacy bit9api (`cbapi.bit9Api`) are still compatible with Python 2.x only.

## Backwards Compatibility

Backwards compatibility with old scripts is maintained through the `cbapi.legacy` module. Old scripts that import
`cbapi.CbApi` directly will continue to work. Once cbapi 2.0.0 is released, the old `CbApi` will be deprecated and
removed entirely no earlier than January 2017.

New scripts should use the `cbapi.CbResponseAPI` (for Cb Response) and 
`cbapi.CbProtectionAPI` (for Cb Protection / former Bit9) API entry points.

## Getting Started

There are two ways to get started:

1. If you want to install the latest stable version of `cbapi`, simply install via `pip`:

        pip install cbapi

2. If you want to change cbapi itself, then you will want to install cbapi in "develop" mode.
Clone this repository, cd into `cbapi-python` then run setup.py with the `develop` flag:

        python setup.py develop
    
### Sample Code

There are several examples in the `examples` directory for both Carbon Black Enterprise Response and Protection. We
will be adding more samples over time. For a quick start, see the following code snippets:

**Carbon Black Enterprise Response**
    
    from cbapi.response.models import Process, Binary, Sensor, Feed, Watchlist, Investigation
    from cbapi.response.rest_api import CbEnterpriseResponseAPI
    
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    c=CbEnterpriseResponseAPI()
    
    # read the first four bytes of the notepad.exe associated with the first process instance of notepad running
    c.select(Process).where('process_name:notepad.exe').first().binary.file.read(4)

    # if you want a specific ID, you can put it straight into the .select() call:
    binary = c.select(Binary, "24DA05ADE2A978E199875DA0D859E7EB")
    
    # isolate all sensors who ran executable_name.exe
    sensors = set()
    for proc in c.select(Process).where('process_name:executable_name.exe'):
        sensors.add(proc.sensor)
    
    for s in sensors:
        s.network_isolation_enabled = True
        s.save()
    
    
**Carbon Black Enterprise Protection**
    
    from cbapi.protection.models import *
    from cbapi.protection.rest_api import CbEnterpriseProtectionAPI
    
    p=CbEnterpriseProtectionAPI()
    
    # Select the first file instance
    fi = p.select(FileInstance).first()
    
    # print that computer's hostname
    fi.computer.name
    
    # change the policy ID
    fi.computer.policyId = 3
    fi.computer.save()
    
    
### API Token

In order to perform any queries via the API, you will need to get the API token for your Cb user. See the documentation
on the Developer Network website on how to acquire the API token for 
[Enterprise Response](http://developer.carbonblack.com/reference/enterprise-response/authentication/) or
[Enterprise Protection](http://developer.carbonblack.com/reference/enterprise-protection/authentication/)

Once you acquire your API token, place it in one of the default credentials file locations:

* ``/etc/carbonblack/credentials.response`` (or ``.protection`` for Cb Enterprise Protection)
* ``~/.carbonblack/credentials.response``
* (current working directory) ``.carbonblack/credentials.response``

Credentials found in a later path will overwrite earlier ones.

The credentials are stored in INI format. The name of each credential profile is enclosed in square brackets, followed
by comma separated key-value pairs providing the necessary credential information:

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
