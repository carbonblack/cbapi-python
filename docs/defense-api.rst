.. _defense_api:

Cloud Endpoint Standard API
===========================

This page documents the public interfaces exposed by cbapi when communicating with a Cloud Endpoint Standard server.

Main Interface
--------------

To use cbapi with VMware Carbon Black Cloud Endpoint Standard, you will be using the CBDefenseAPI.
The CBDefenseAPI object then exposes two main methods to select data on the Carbon Black server:

.. autoclass:: cbapi.psc.defense.rest_api.CbDefenseAPI
    :members:
    :inherited-members:

    .. :automethod:: select
    .. :automethod:: create

Queries
-------

.. autoclass:: cbapi.psc.defense.rest_api.Query
    :members:


Models
------

.. automodule:: cbapi.psc.defense.models
    :members:
    :undoc-members:
