.. _threathunter_api:

VMware Carbon Black Cloud Enterprise EDR API
============================================

This page documents the public interfaces exposed by cbapi when communicating with a
VMware Carbon Black Cloud Enterprise EDR server.

Main Interface
--------------

To use cbapi with Enterprise EDR, you use CbThreatHunterAPI objects.
These objects expose two main methods to access data on the Enterprise EDR server: ``select`` and ``create``.

.. autoclass:: cbapi.psc.threathunter.rest_api.CbThreatHunterAPI
    :members:
    :inherited-members:

Queries
-------

The Enterprise EDR API uses QueryBuilder instances to construct structured
or unstructured (i.e., raw string) queries. You can either construct these
instances manually, or allow ``CbThreatHunterAPI.select()`` to do it for you:

.. autoclass:: cbapi.psc.threathunter.query.QueryBuilder
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.query.Query
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.AsyncProcessQuery
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.query.FeedQuery
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.query.ReportQuery
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.query.WatchlistQuery
    :members:
    :inherited-members:

Models
------

.. autoclass:: cbapi.psc.threathunter.models.Process
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.Event
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.Tree
    :members:

.. autoclass:: cbapi.psc.threathunter.models.Feed
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.Report
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.IOC
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.IOC_V2
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.Watchlist
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.ReportSeverity
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.Binary
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.threathunter.models.Downloads
    :members:
    :inherited-members:
