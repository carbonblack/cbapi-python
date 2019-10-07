.. _psc_api:

CB PSC API
==========

This page documents the public interfaces exposed by cbapi when communicating with
the Carbon Black Predictive Security Cloud (PSC).

Main Interface
--------------

To use cbapi with the Carbon Black PSC, you use CbPSCBaseAPI objects.

.. autoclass:: cbapi.psc.rest_api.CbPSCBaseAPI
    :members:
    :inherited-members:

Device API
----------

The PSC can be used to enumerate devices within your organization, and change their
status via a control request.

You can use the select() method on the CbPSCBaseAPI to create a query object for
Device objects, which can be used to locate a list of Devices.

*Example:*

	>>> cbapi = CbPSCBaseAPI(...)
	>>> devices = cbapi.select(Device).os("LINUX").status("ALL")

Selects all devices running Linux from the current organization.

**Query Object:**

.. autoclass:: cbapi.psc.query.DeviceSearchQuery
	:members:
	
**Model Object:**

.. autoclass:: cbapi.psc.models.Device
	:members:
	:undoc-members:
	
