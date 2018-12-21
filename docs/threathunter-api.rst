.. _threathunter_api:

Cb ThreatHunter API
===================

This page documents the public interfaces exposed by cbapi when communicating with a
Carbon Black PSC ThreatHunter server.

Main Interface
--------------

To use cbapi with Carbon Black ThreatHunter, you will be using the CbThreatHunterAPI.
The CbThreatHunterAPI object then exposes two main methods to access data on the
Carbon Black server: ``select`` and ``create``.

.. autoclass:: cbapi.psc.threathunter.rest_api.CbThreatHunterAPI
    :members:
    :inherited-members:

Queries
-------

The ThreatHunter API uses QueryBuilder instances to construct structured
or unstructured (i.e., raw string) queries. You can either construct these
instances manually, or allow ``CbThreatHunterAPI.select()`` to do it for you:

.. autoclass:: cbapi.psc.threathunter.query.QueryBuilder
    :members:

.. autoclass:: cbapi.psc.threathunter.query.Query
    :members:
.. autoclass:: cbapi.psc.threathunter.models.AsyncProcessQuery
    :members:

Models
------

.. autoclass:: cbapi.psc.threathunter.models.Process
    :members:
.. autoclass:: cbapi.psc.threathunter.models.Event
    :members:
.. autoclass:: cbapi.psc.threathunter.models.Tree
    :members:

