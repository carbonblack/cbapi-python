.. _protection_api:

Carbon Black Protection REST API
================================

This page documents the public interfaces exposed by cbapi when communicating with a Carbon Black Enterprise
Protection server.

Main Interface
--------------

To use cbapi with Carbon Black Protection, you will be using the CbEnterpriseProtectionAPI.
The CbEnterpriseProtectionAPI object then exposes two main methods to select data on the Carbon Black server:

.. autoclass:: cbapi.protection.rest_api.CbEnterpriseProtectionAPI
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

.. autoclass:: cbapi.protection.models.Computer
    :members:
    :inherited-members:
