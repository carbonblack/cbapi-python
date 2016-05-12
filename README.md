# Python bindings for Carbon Black REST API

https://www.bit9.com/solutions/carbon-black/

## Support

If you have questions on the Carbon Black API or these API Bindings, please contact us at dev-support@carbonblack.com.
Also review the documentation and guides available on the 
[Carbon Black Developer Network website](http://developer.carbonblack.com)

## Requirements

The new cbapi is designed to work on Python 2.6.6 and above (including 3.x). 
All requirements are installed as part of `pip install`. 
The legacy cbapi (`cbapi.CbApi`) and legacy bit9api (`cbapi.bit9Api`) are still compatible with Python 2.x only.

## Backwards Compatibility

Backwards compatibility with old scripts is maintained through the `cbapi.legacy` module. Old scripts that import
`cbapi.CbApi` directly will continue to work. Once cbapi 2.0.0 is released, the old `CbApi` will be deprecated and
removed entirely no earlier than January 2017.

New scripts should use the `cbapi.CbEnterpriseResponseAPI` (for Carbon Black "Enterprise Response") and 
`cbapi.CbEnterpriseProtectionAPI` (for Carbon Black "Enterprise Protection" / former Bit9) API entry points.

## Getting Started

### Development

Prerequisites:

```
pip install py-lru-cache
pip install attrdict
pip install six
pip install total-ordering
```

### Installation

    pip install cbapi

### Sample Code

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
    
    # isolate all sensors who ran notepad.exe
    sensors = set()
    for proc in c.select(Process).where('process_name:notepad.exe'):
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

* `/etc/carbonblack/credentials.response` (or `.protection` for Cb Enterprise Protection)
* `~/.carbonblack/credentials.response`
* (current working directory) `.carbonblack/credentials.response`

Credentials found in a later path will overwrite earlier ones.

The credential file is stored as an INI file:

```
[default]
url=https://localhost
token=abcdef0123456789abcdef
ssl_verify=False
```
