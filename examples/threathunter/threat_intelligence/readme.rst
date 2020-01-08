.. _readme:

ThreatIntel Module
==================

Python3 module that can be used in the development of Threat
Intelligence Connectors for the Carbon Black Cloud.

Dependencies
------------

The file ``requirements.txt`` contains a list of dependencies. After cloning this repository, run the following command from
the ``examples/threathunter/threat_intelligence`` directory:

.. code:: python

   pip3 install -r ./requirements.txt

Introduction
------------

This document describes how to use the ThreatIntel Python3 module for
development of connectors that retrieve Threat Intelligence and import
it into a Carbon Black Cloud instance. Documentation on Feed and Report
definitions is `available
here. <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions>`__

Usage
-----

``threatintel.py`` has two main uses:

1. Report Validation
2. Pushing Reports to a Carbon Black ThreatHunter Feed.

Report Validation
~~~~~~~~~~~~~~~~~

Each Report to be sent to the Carbon Black Cloud should be validated
before sending. The ThreatHunter Report format is a JSON object with
five required and five optional values.

=============== ======= ============== ==============
Required        Type    Optional       Type
=============== ======= ============== ==============
``id``          string  ``link``       string
``timestamp``   integer ``[tags]``     [str]
``title``       string  ``iocs``       IOC Format
``description`` string  ``[iocs_v2]``  [IOCv2 Format]
``severity``    integer ``visibility`` string
=============== ======= ============== ==============

The ``input_validation`` function checks for the existence and type of the five
required values, and (if applicable) checks the optional values. The
function takes a list of dictionaries as input, and outputs a Boolean
indicating if validation was successful.

Pushing Reports to a Carbon Black ThreatHunter Feed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``push_to_cb`` function takes a list of ``AnalysisResult`` objects (or objects of your own custom class) and a Carbon
Black ThreatHunter Feed ID as input, and writes output to the console.
The ``AnalysisResult`` class is defined in ``results.py``, and requirements for a custom class are outlined in the Customization section below.

``AnalysisResult`` objects are expected to have the same properties as
ThreatHunter Reports (listed in the table above in Report Validation), with the addition of ``iocs_v2``. The
``push_to_cb`` function will convert ``AnalysisResult`` objects into
Report dictionaries, and then those dictionaries into ThreatHunter
Report objects.

Report dictionaries are passed through the Report validation function
``input_validation`` described above. Any improperly formatted report
dictionaries are saved to a file called ``reports.json``.

Upon successful sending of reports to a ThreatHunter Feed, you should
see something similar to the following INFO message in the console:

``INFO:threatintel:Appended 1000 reports to ThreatHunter Feed AbCdEfGhIjKlMnOp``


Using Validation and Pushing to ThreatHunter in your own code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Import the module and supporting classes like any other python package:

.. code:: python

  from threatintel import ThreatIntel
  from results import IOC_v2, AnalysisResult
  ti = ThreatIntel()

Take the threat intelligence data from your source, and convert it into ``AnalysisResult`` objects.

.. code:: python

  result = AnalysisResult(
                         analysis_name=analysis_name,
                         scan_time=scan_time,
                         score=score,
                         title=title,
                         description=description)


  ti.push_to_cb(feed_id='AbCdEfGhIjKlMnOp', results=)


Customization
-------------

Although the ``AnalysisResult`` class is provided in ``results.py`` as
an example, you may create your own custom class to use with the
``push_to_cb`` function. The class must have the following attributes to work
with the provided ``push_to_cb`` and ``input_validation`` functions, as
well as the ThreatHunter backend:

=============== =========
Attribute       Type
=============== =========
``id``          string
``timestamp``   integer
``title``       string
``description`` string
``severity``    integer
``iocs_v2``     [iocs_v2]
=============== =========

It is strongly recommended to use the provided ``IOC_v2`` class from
``results.py``. If you are using a custom ``iocs_v2`` class, you must
create a method called ``as_dict`` that returns ``id``, ``match_type``,
``values``, ``field``, and ``link`` as a dictionary, in order to be compatible with
the ``push_to_cb`` function.

Developing New ThreatIntel Sources
----------------------------------

To integrate threat intelligence into a Carbon Black ThreatHunter Feed,
the threat intelligence must be formatted into Reports that are
palatable to ThreatHunter. Reports are `defined
here <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/feed-api/#definitions>`__.
Although not required, the parameter ``iocs_v2`` is recommended to make
your data useful.

ThreatHunter ``Reports`` can be built using dictionaries. This
ThreatIntel module builds reports with the following method:

.. code:: python

   report = Report(self.cb, initial_data=report_dict, feed_id=feed_id)

This takes an instance of ``cbapi.psc.threathunter.CbThreatHunterAPI``
as ``self.cb``, a report dictionary as ``report_dict``, and a
ThreatHunter Feed ID to send the report to as ``feed_id``.

The ``report_dict`` dictionary is generated in
``ThreatIntel.push_to_cb()`` by extracting required parameters from
``AnalysisResult`` objects, as well as any IOCs attached to the result.

Writing a Custom Threat Intelligence Polling Connector
------------------------------------------------------

An example of a custom Threat Intel connector that uses the
``ThreatIntel`` Python3 module is included in this repository as
``stix_taxii.py``. Most use cases will warrant the use of the
ThreatHunter ``Report`` attribute ``iocs_v2``, so it is included in
``ThreatIntel.push_to_cb()``.

``ThreatIntel.push_to_cb()`` and ``AnalysisResult`` can be adapted to
include other ThreatHunter ``Report`` attributes like
``link, tags, iocs, and visibility``.

Using ``ThreatIntel.push_to_cb(feed_id, results)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After writing the code required to connect and ingest Threat
Intelligence from your chosen source, it must be formatted before
sending it to the Carbon Black Cloud. It is recommended that you use the
existing ``AnalysisResult`` and ``IOC_v2`` classes to make interfacing
with Carbon Black easier.

After ingesting data from your chosen source, feed it into
``AnalysisResult`` objects, which can have attached ``IOC_v2``\ ’s.
These ``AnalysisResult`` objects can then be fed into
``ThreatIntel.push_to_cb()`` as a list, and will be validated and sent
to your specified ThreatHunter ``feed_id``.
