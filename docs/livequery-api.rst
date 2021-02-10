.. _livequery_api:

CB LiveQuery API
================

This page documents the public interfaces exposed by cbapi when communicating with Carbon Black LiveQuery devices.

Main Interface
--------------

To use cbapi with Carbon Black LiveQuery, you use CbLiveQueryAPI objects.

The LiveQuery API is used in two stages: run submission and result retrieval.

.. autoclass:: cbapi.psc.livequery.rest_api.CbLiveQueryAPI
    :members:
    :inherited-members:

Queries
-------

The LiveQuery API uses QueryBuilder instances to construct structured or unstructured (i.e., raw string) queries.
You can either construct these instances manually, or allow ``CbLiveQueryAPI.select()`` to do it for you:

.. autoclass:: cbapi.psc.livequery.query.QueryBuilder
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.livequery.query.RunQuery
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.livequery.models.ResultQuery
    :members:
    :inherited-members:

Models
------

.. autoclass:: cbapi.psc.livequery.models.Run
    :members:
    :inherited-members:

.. autoclass:: cbapi.psc.livequery.models.Result
    :members:
    :inherited-members:

