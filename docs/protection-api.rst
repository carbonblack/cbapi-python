.. _protection_api:

Carbon Black App Control (CB Protection) API
===========================================

This page documents the public interfaces exposed by cbapi when communicating with a Carbon Black App Control (Enterprise
Protection) server.

Main Interface
--------------

To use cbapi with Carbon Black App Control (CB Protection), you will be using the CbProtectionAPI.
The CbProtectionAPI object then exposes two main methods to select data on the Carbon Black server:

.. autoclass:: cbapi.protection.rest_api.CbProtectionAPI
    :members:
    :inherited-members:

    .. :automethod:: select
    .. :automethod:: create

Queries
-------

.. autoclass:: cbapi.protection.rest_api.Query
    :members:


Models
------

.. automodule:: cbapi.protection.models
    :members:
    :undoc-members:
