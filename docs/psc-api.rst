.. _psc_api:

VMware Carbon Black Cloud API
=============================

This page documents the public interfaces exposed by cbapi when communicating with the VMware Carbon Black Cloud.

Main Interface
--------------

To use cbapi with the VMware Carbon Black Cloud, you use CbPSCBaseAPI objects.

.. autoclass:: cbapi.psc.rest_api.CbPSCBaseAPI
    :members:
    :inherited-members:

Device API
----------

The Carbon Black Cloud can be used to enumerate devices within your organization, and change their
status via a control request.

You can use the select() method on the CbPSCBaseAPI to create a query object for
Device objects, which can be used to locate a list of Devices.

*Example:*

	>>> cbapi = CbPSCBaseAPI(...)
	>>> devices = cbapi.select(Device).set_os("LINUX").status("ALL")

Selects all devices running Linux from the current organization.

**Query Object:**

.. autoclass:: cbapi.psc.devices_query.DeviceSearchQuery
	:members:

**Model Object:**

.. autoclass:: cbapi.psc.models.Device
	:members:
	:undoc-members:

Alerts API
----------

Using the API, you can search for alerts within your organization, and dismiss or undismiss them, either individually
or in bulk.

You can use the select() method on the CbPSCBaseAPI to create a query object for BaseAlert objects, which can be used
to locate a list of alerts.  You can also search for more specialized alert types:

* CBAnalyticsAlert - Alerts from CB Analytics
* VMwareAlert - Alerts from VMware
* WatchlistAlert - Alerts from watch lists

*Example:*

	>>> cbapi = CbPSCBaseAPI(...)
	>>> alerts = cbapi.select(BaseAlert).set_device_os(["WINDOWS"]).set_process_name(["IEXPLORE.EXE"])

Selects all alerts on a Windows device running the Internet Explorer process.

Individual alerts may have their status changed using the dismiss() or update()
methods on the BaseAlert object.  To dismiss multiple alerts at once, you can use
the dismiss() or update() methods on the standard query, after adding criteria to it.
This method returns a request ID, which can be used to create a WorkflowStatus object;
querying this object's "finished" property will let you know when the operation is
finished.

*Example:*

	>>> cbapi = CbPSCBaseAPI(...)
	>>> query = cbapi.select(BaseAlert).set_process_name(["IEXPLORE.EXE"])
	>>> reqid = query.dismiss("Using Chrome")
	>>> stat = cbapi.select(WorkflowStatus, reqid)
	>>> while not stat.finished:
	>>>     # wait for it to finish

This dismisses all alerts which reference the Internet Explorer process.

**Query Objects:**

.. autoclass:: cbapi.psc.alerts_query.BaseAlertSearchQuery
	:members:

.. autoclass:: cbapi.psc.alerts_query.CBAnalyticsAlertSearchQuery
	:members:

.. autoclass:: cbapi.psc.alerts_query.VMwareAlertSearchQuery
	:members:

.. autoclass:: cbapi.psc.alerts_query.WatchlistAlertSearchQuery
	:members:

**Model Objects:**

.. autoclass:: cbapi.psc.models.Workflow
	:members:
	:undoc-members:

.. autoclass:: cbapi.psc.models.BaseAlert
	:members:
	:undoc-members:

.. autoclass:: cbapi.psc.models.CBAnalyticsAlert
	:members:
	:undoc-members:

.. autoclass:: cbapi.psc.models.VMwareAlert
	:members:
	:undoc-members:

.. autoclass:: cbapi.psc.models.WatchlistAlert
	:members:
	:undoc-members:

.. autoclass:: cbapi.psc.models.WorkflowStatus
	:members:
	:undoc-members:
