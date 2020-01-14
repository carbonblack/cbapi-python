# ThreatIntel Module
Python3 module that can be used in the development of Threat Intelligence Connectors for the Carbon Black Cloud.

## Requirements

The file `requirements.txt` contains a list of dependencies for this project. After cloning this repository, run the following command from the `examples/threathunter/threat_intelligence` directory:

```python
pip3 install -r ./requirements.txt
```


## Introduction
This document describes how to use the ThreatIntel Python3 module for development of connectors that retrieve Threat Intelligence and import it into a Carbon Black Cloud instance.

Throughout this document, there are references to Carbon Black ThreatHunter Feed and Report formats. Documentation on Feed and Report definitions is [available here.](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions)

## Example

An example of implementing this ThreatIntel module is [available here](Taxii_README.md). The example uses cabby to connect to a TAXII server, collect threat intelligence, and send it to a ThreatHunter Feed.


## Usage

`threatintel.py` has two main uses:

1. Report Validation with `threatintel.input_validation()`
2. Pushing Reports to a Carbon Black ThreatHunter Feed with `threatintel.push_to_cb()`

### Report validation

Each Report to be sent to the Carbon Black Cloud should be validated
before sending. The [ThreatHunter Report format](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions) is a JSON object with
five required and five optional values.

|Required|Type|Optional|Type|
|---|---|---|---|
|`id`|string|`link`|string|
|`timestamp`|integer|`[tags]`|[str]|
|`title`|string|`iocs`|[IOC Format](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions)|
|`description`|string|`[iocs_v2]`|[[IOCv2 Format](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions)]|
|`severity`|integer|`visibility`|string|

The `input_validation` function checks for the existence and type of the five
required values, and (if applicable) checks the optional values. The
function takes a list of dictionaries as input, and outputs a Boolean
indicating if validation was successful.

### Pushing Reports to a Carbon Black ThreatHunter Feed

The `push_to_cb` function takes a list of `AnalysisResult` objects (or objects of your own custom class) and a Carbon
Black ThreatHunter Feed ID as input, and writes output to the console.
The `AnalysisResult` class is defined in `results.py`, and requirements for a custom class are outlined in the Customization section below.

`AnalysisResult` objects are expected to have the same properties as
ThreatHunter Reports (listed in the table above in Report Validation), with the addition of `iocs_v2`. The
`push_to_cb` function will convert `AnalysisResult` objects into
Report dictionaries, and then those dictionaries into ThreatHunter
Report objects.

Report dictionaries are passed through the Report validation function
`input_validation` described above. Any improperly formatted report
dictionaries are saved to a file called `malformed_reports.json`.

Upon successful sending of reports to a ThreatHunter Feed, you should
see something similar to the following INFO message in the console:

`INFO:threatintel:Appended 1000 reports to ThreatHunter Feed AbCdEfGhIjKlMnOp`


### Using Validation and Pushing to ThreatHunter in your own code

Import the module and supporting classes like any other python package, and instantiate a ThreatIntel object:

 ```python
  from threatintel import ThreatIntel
  from results import IOC_v2, AnalysisResult
  ti = ThreatIntel()
```

Take the threat intelligence data from your source, and convert it into ``AnalysisResult`` objects. Then, attach the indicators of compromise, and store your data in a list.

```python
  myResults = []
  for intel in myThreatIntelligenceData:
    result = AnalysisResult(analysis_name=intel.name, scan_time=intel.scan_time, score=intel.score, title=intel.title, description=intel.description)
    #ioc_dict could be a collection of md5 hashes, dns values, file hashes, etc.
    for ioc_key, ioc_val in intel.ioc_dict.items():
      result.attach_ioc_v2(values=ioc_val, field=ioc_key, link=link)
    myResults.append(result)
```

Finally, push your threat intelligence data to a ThreatHunter Feed.
```python
  ti.push_to_cb(feed_id='AbCdEfGhIjKlMnOp', results=myResults)
```

`ti.push_to_cb` automatically validates your input to ensure it has the values required for ThreatHunter. Validated reports will be sent to your specified ThreatHunter Feed, and any malformed reports will be available for review locally at `malformed_reports.json`.



## Customization

Although the `AnalysisResult` class is provided in `results.py` as an example, you may create your own custom class to use with `push_to_cb`. The class must have the following attributes to work with the provided `push_to_cb` and `input_validation` functions, as well as the ThreatHunter backend:


|Attribute|Type|
|---|---|
|`id`|string|
|`timestamp`|integer|
|`title`|string|
|`description`|string|
|`severity`|integer|
|`iocs_v2`|[[IOCv2 Format](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions)]|

It is strongly recommended to use the provided `IOC_v2()` class from `results.py`. If you decide to use a custom `iocs_v2` class, that class must have a method called `as_dict` that returns `id`, `match_type`, `values`, `field`, and `link` as a dictionary.


## Writing a Custom Threat Intelligence Polling Connector

An example of a custom Threat Intel connector that uses the `ThreatIntel` Python3 module is included in this repository as `stix_taxii.py`. Most use cases will warrant the use of the ThreatHunter `Report` attribute `iocs_v2`, so it is included in `ThreatIntel.push_to_cb()`.

`ThreatIntel.push_to_cb()` and `AnalysisResult` can be adapted to include other ThreatHunter `Report` attributes like `link, tags, iocs, and visibility`.


## Troubleshooting

### Credential Error
In order to use this code, you must have CBAPI installed and configured. If you receive the following message, visit the CBAPI GitHub repository for [instructions on setting up authentication](https://github.com/carbonblack/cbapi-python#api-token).

### 504 Gateway Timeout Error
The [Carbon Black ThreatHunter Feed Manager API](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/) is used in this code. When posting to a Feed, there is a 60 second limit before the gateway terminates your connection. The amount of reports you can POST to a Feed is limited by your connection speed. In this case, you will have to split your threat intelligence into smaller collections until the request takes less than 60 seconds, and send each smaller collection to an individual ThreatHunter Feed.
