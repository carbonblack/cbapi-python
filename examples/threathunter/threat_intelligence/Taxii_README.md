# TAXII Connector
Connector for pulling and converting STIX information from TAXII Service Providers into CB Feeds.

## Requirements/Installation

The file `requirements.txt` contains a list of dependencies for this project. After cloning this repository, run the following command from the `examples/threathunter/threat_intelligence` directory:

```python
pip3 install -r ./requirements.txt
```

## Introduction
This document describes how to configure the CB ThreatHunter TAXII connector.
This connector allows for the importing of STIX data by querying one or more TAXII services, retrieving that data and then converting it into CB feeds using the CB JSON format for IOCs.

## Setup - TAXII Configuration File
The TAXII connector uses the configuration file `config.yml`. An example configuration file is available [here.](config.yml) An explanation of each entry in the configuration file is provided in the example.


## Running the Connector
The connector can be activated by running the Python3 file `stix_taxii.py`. The connector will attempt to connect to your TAXII service(s), poll the collection(s), retrieve the STIX data, and send it to the ThreatHunter Feed specified in your `config.yml` file.

```python
python3 stix_taxii.py
```

If running this script on a schedule, the `start_date` for each TAXII service can be updated via command line arguments. To change the value for each site in your config file, you must supply the site name and desired `start_date` in `%Y-%m-%d %H:%M:%S` format.

```python
python3 stix_taxii.py my_site_name_1 '2019-11-05 00:00:00' my_site_name_2 '2019-11-05 00:00:00'
```

This may be useful if the intention is to keep an up-to-date collection of STIX data in a ThreatHunter Feed.

## Troubleshooting

### Credential Error
In order to use this code, you must have CBAPI installed and configured. If you receive the following message, visit the CBAPI GitHub repository for [instructions on setting up authentication](https://github.com/carbonblack/cbapi-python#api-token).

### 504 Gateway Timeout Error
The [Carbon Black ThreatHunter Feed Manager API](https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/) is used in this code. When posting to a Feed, there is a 60 second limit before the gateway terminates your connection. The amount of reports you can POST to a Feed is limited by your connection speed. In this case, you will have to split your threat intelligence into smaller collections until the request takes less than 60 seconds, and send each smaller collection to an individual ThreatHunter Feed.
