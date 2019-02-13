.. _defense_api:

Cb Defense API
==============

This page documents the public interfaces exposed by cbapi when communicating with a Cb Defense server.

Main Interface
--------------

To use cbapi with Carbon Black Defense, you will be using the CbDefenseAPI.
The CbDefenseAPI object then exposes two main methods to select data on the Carbon Black server:

.. autoclass:: cbapi.defense.psc.rest_api.CbDefenseAPI
    :members:
    :inherited-members:

    .. :automethod:: select
    .. :automethod:: create

Queries
-------

.. autoclass:: cbapi.defense.psc.rest_api.Query
    :members:


Models
------

.. automodule:: cbapi.defense.psc.models
    :members:
    :undoc-members:
