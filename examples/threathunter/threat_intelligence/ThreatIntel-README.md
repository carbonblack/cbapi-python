# ThreatIntel Module
Python3 module that can be used in the development of Threat Intelligence Connectors for the Carbon Black Cloud.

## Requirements/Installation

The file `requirements.txt` contains a list of dependencies for this project. After cloning this repository, run the following command from the `examples/threathunter/threat_intelligence` directory:

```
pip install -r ./requirements.txt
```


## Introduction
This document describes how to use the ThreatIntel Python3 module for development of connectors that retrieve Threat Intelligence and import it into a Carbon Black Cloud instance. This document describes how to use the ThreatIntel Python3 module for development of connectors that retrieve Threat Intelligence and import it into a Carbon Black Cloud instance. Documentation on Feed and Report definitions is [available here.](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions)

The ThreatIntel `push_to_cb` method expects a list of objects that have six attributes:
`id, timestamp, title, description, severity, and iocs_v2`. For these objects, may use the pre-built `AnalysisResult` class from `results.py`, which has these attributes already, or build your own custom class.

### Files

#### `threatintel.py`

Contains the `ThreatIntel` class. This converts Threat Intelligence from result dictionaries into ThreatHunter `Reports`, and then sends them to a ThreatHunter `Feed`.

#### `results.py`

Contains the `AnalysisResult` and `IOC_v2` classes. This contains the logic to attach `iocs_v2` dictionaries to `AnalysisResult` objects.

### Important ThreatIntel Methods

#### `ThreatIntel.push_to_cb(feed_id, results)`:
Input a ThreatHunter Feed ID and a list of result objects. The result objects must contain the following required attributes: `id, timestamp, title, description, severity, and iocs_v2`. Formats the result objects into ThreatHunter `Report` objects, calls the input validation function, then sends the `Report` objects to a ThreatHunter `Feed`.

#### `ThreatIntel.input_validation(reports)`:
Input a list of `Report` dictionaries, and outputs a boolean value indicating if the dictionaries are properly formatted for submission to a ThreatHunter `Feed`.


## Data Classes

### ThreatHunter Report
CBAPI includes the `cbapi.psc.threathunter.Report` class. ThreatHunter `Report` objects have the following required and optional parameters:

|Required|Type|Optional|Type|
|---|---|---|---|
|`id`|string|`link`|string|
|`timestamp`|integer|`[tags]`|[str]|
|`title`|string|`iocs`|IOC Format| #document IOC Format
|`description`|string|`[iocs_v2]`|[IOCv2 Format]| #document IOCv2 Format
|`severity`|integer|`visibility`|string|

Note: `IOC` and `IOC_v2` definitions are [available here.](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions)

ThreatHunter `Reports` can be built using dictionaries. This ThreatIntel module builds reports with the following method:

```python
report = Report(self.cb, initial_data=report_dict, feed_id=feed_id)
```

This takes an instance of `cbapi.psc.threathunter.CbThreatHunterAPI` as `self.cb`, a report dictionary as `report_dict`, and a ThreatHunter Feed ID to send the report to as `feed_id`.

The `report_dict` dictionary is generated in `ThreatIntel.push_to_cb()` by extracting required parameters from `AnalysisResult` objects, as well as any IOCs attached to the result.

### AnalysisResult

The `results.py` file contains the `AnalysisResult` class. When initiating a new result, the class expects the following attributes: `analysis_name, scan_time, title, description, score`. You may create your own custom class for a result object, but to use it with the included `ThreatIntel` class, it must include these five attrbutes:


|Required|Type|
|---|---|
|`analysis_name`|string|
|`scan_time`|integer|
|`title`|string|
|`description`|string|
|`score`|integer|


Here is part of the `AnalysisResult` class from `results.py`:

```python
class AnalysisResult():
    """
    Models the result of an analysis performed by a connector.
    """

    def __init__(self, analysis_name, scan_time, score, title, description):
        self.id = str(analysis_name)
        self.timestamp = scan_time
        self.title = title
        self.description = description
        self.severity = score
        self.link = None
        self.tags = None
        self.iocs = []
        self.iocs_v2 = []
        self.visibility = None
        self.connector_name = "STIX_TAXII"


    def attach_ioc_v2(self, *, match_type=IOC_v2.MatchType.Equality, values, field, link):
        self.iocs_v2.append(IOC_v2(analysis=self.id, match_type=match_type, values=values, field=field, link=link))
```

### IOC

The `results.py` file contains the `IOC` class. When attaching an IOC to a result, you can use the function `AnalysisResult.attach_ioc_v2()`. IOCs have the following required and optional parameters:


|Required|Type|Optional|Type|
|---|---|---|---|
|`id`|string|`field`|string|
|`match_type`|integer|`link`|str|
|`values`|string|||

Here is part of the `IOC_v2` class from `results.py`:

```python
class IOC_v2():
    """
    Models an indicator of compromise detected during an analysis.

    Every IOC belongs to an AnalysisResult.
    """

    def __init__(self, analysis, match_type, values, field, link):
        self.id = analysis
        self.match_type = match_type
        self.values = values
        self.field = field
        self.link = link
```

## Writing a Custom Threat Intelligence Polling Connector

An example of a custom Threat Intel connector that uses the `ThreatIntel` Python3 module is included in this repository as `stix_taxii.py`. Most use cases will warrant the use of the ThreatHunter `Report` attribute `iocs_v2`, so it is included in `ThreatIntel.push_to_cb()`. Other useful items include the `AnalysisResult` and `IOC_v2` classes in `results.py`.

`ThreatIntel.push_to_cb()` and `AnalysisResult` can be adapted to include other ThreatHunter `Report` attributes like `link, tags, iocs, and visibility`.

#### Using `ThreatIntel.push_to_cb(feed_id, results)`

After writing the code required to connect and ingest Threat Intelligence from your chosen source, it must be formatted before sending it to the Carbon Black Cloud. It is recommended that you use the existing `AnalysisResult` and `IOC_v2` classes to make interfacing with Carbon Black easier.

After ingesting data from your chosen source, feed it into `AnalysisResult` objects, which can have attached `IOC_v2`'s. These `AnalysisResult` objects can then be fed into `ThreatIntel.push_to_cb()` as a list, and will be validated and sent to your specified ThreatHunter `feed_id`.
