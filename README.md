# Python bindings for Carbon Black REST API

**Latest Version: 1.7.5**

_**Notice**: The Carbon Black Cloud portion of CBAPI has moved to https://github.com/carbonblack/carbon-black-cloud-sdk-python. Any future development and bug fixes for Carbon Black Cloud APIs will be made there. Carbon Black EDR and App Control will remain supported at CBAPI_

These are the Python bindings for the Carbon Black Enterprise Response and Enterprise Protection REST APIs.
To learn more about the REST APIs, visit the Carbon Black Developer Network Website at https://developer.carbonblack.com.

Please visit https://cbapi.readthedocs.io for detailed documentation on this API. Additionally, we have a slideshow
available at https://developer.carbonblack.com/2016/07/presentation-on-the-new-carbon-black-python-api/ that provides
an overview of the concepts that underly this API binding.

## Support

1. View all API and integration offerings on the [Developer Network](https://developer.carbonblack.com/) along with reference documentation, video tutorials, and how-to guides.
2. Use the [Developer Community Forum](https://community.carbonblack.com/t5/Developer-Relations/bd-p/developer-relations) to discuss issues and get answers from other API developers in the Carbon Black Community.
3. Report bugs and change requests to [Carbon Black Support](http://carbonblack.com/resources/support/).

## Requirements

The new cbapi is designed to work on Python 2.6.6 and above (including 3.x). If you're just starting out,
we recommend using the latest version of Python 3.6.x or above.

All requirements are installed as part of `pip install`.
The legacy cbapi (`cbapi.CbApi`) and legacy bit9api (`cbapi.bit9Api`) are still compatible with Python 2.x only.

## Backwards Compatibility

Backwards compatibility with old scripts is maintained through the `cbapi.legacy` module. Old scripts that import
`cbapi.CbApi` directly will continue to work. Once cbapi 2.0.0 is released, the old `CbApi` will be deprecated and
removed entirely no earlier than January 2017.

New scripts should use the `cbapi.CbResponseAPI` (for CB Response) and
`cbapi.CbProtectionAPI` (for CB Protection / former Bit9) API entry points.

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

In order to perform any queries via the API, you will need to get the API token for your CB user. See the documentation
on the Developer Network website on how to acquire the API token for
[CB Response](http://developer.carbonblack.com/reference/enterprise-response/authentication/),
[CB Protection](http://developer.carbonblack.com/reference/enterprise-protection/authentication/), or
[CB Defense](http://developer.carbonblack.com/reference/cb-defense/authentication/).

Once you acquire your API token, place it in one of the default credentials file locations:

* ``/etc/carbonblack/``
* ``~/.carbonblack/``
* ``/current_working_directory/.carbonblack/``

For distinction between credentials of different Carbon Black products, use the following naming convention for your credentials files:

* ``credentials.psc`` for CB Defense, CB ThreatHunter, and CB LiveOps
* ``credentials.response`` for CB Response
* ``credentials.protection`` for CB Protection

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

* **url**: The base URL of the CB server. This should include the protocol (https) and the hostname, and nothing else.
* **token**: The API token for the user ID. More than one credential profile can be specified for a given server, with
  different tokens for each.
* **ssl_verify**: True or False; controls whether the SSL/TLS certificate presented by the server is validated against
  the local trusted CA store.
* **org_key**: The organization key. This is required to access the Carbon Black Cloud, and can be found in the console. The format is ``123ABC45``.
* **proxy**: A proxy specification that will be used when connecting to the CB server. The format is:
  ``http://myusername:mypassword@proxy.company.com:8001/`` where the hostname of the proxy is ``proxy.company.com``, port
  8001, and using username/password ``myusername`` and ``mypassword`` respectively.
* **ignore_system_proxy**: If you have a system-wide proxy specified, setting this to True will force cbapi to bypass
  the proxy and directly connect to the CB server.

Future versions of cbapi will also provide the ability to "pin" the TLS certificate so as to provide certificate
verification on self-signed or internal CA signed certificates.
