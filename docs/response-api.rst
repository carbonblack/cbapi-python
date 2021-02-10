.. _response_api:

VMware Carbon Black EDR API
===========================

This page documents the public interfaces exposed by cbapi when communicating with a VMware Carbon Black EDR server.

Main Interface
--------------

To use cbapi with EDR, you will be using the CbResponseAPI.
The CbResponseAPI object then exposes two main methods to access data on the Carbon Black server:
``select`` and ``create``.

.. autoclass:: cbapi.response.rest_api.CbResponseAPI
    :members:
    :inherited-members:

Queries
-------

.. autoclass:: cbapi.response.query.Query
    :members:
.. autoclass:: cbapi.response.models.ProcessQuery
    :members:
.. autoclass:: cbapi.response.models.ThreatReportQuery
    :members:
.. autoclass:: cbapi.response.models.AlertQuery
    :members:

Models
------
.. autoclass:: cbapi.response.models.Process
    :members:
.. autoclass:: cbapi.response.models.Binary
    :members:
.. autoclass:: cbapi.response.models.Sensor
    :members:
.. autoclass:: cbapi.response.models.Feed
    :members:
.. autoclass:: cbapi.response.models.BannedHash
    :members:
.. autoclass:: cbapi.response.models.Watchlist
    :members:
.. autoclass:: cbapi.response.models.Alert
    :members:

Live Response
-------------

.. autoclass:: cbapi.live_response_api.CbLRSessionBase

File Operations
^^^^^^^^^^^^^^^

.. automethod:: cbapi.live_response_api.CbLRSessionBase.get_file
.. automethod:: cbapi.live_response_api.CbLRSessionBase.delete_file
.. automethod:: cbapi.live_response_api.CbLRSessionBase.put_file
.. automethod:: cbapi.live_response_api.CbLRSessionBase.list_directory
.. automethod:: cbapi.live_response_api.CbLRSessionBase.create_directory
.. automethod:: cbapi.live_response_api.CbLRSessionBase.walk

Registry Operations
^^^^^^^^^^^^^^^^^^^

.. automethod:: cbapi.live_response_api.CbLRSessionBase.get_registry_value
.. automethod:: cbapi.live_response_api.CbLRSessionBase.set_registry_value
.. automethod:: cbapi.live_response_api.CbLRSessionBase.delete_registry_value
.. automethod:: cbapi.live_response_api.CbLRSessionBase.create_registry_key
.. automethod:: cbapi.live_response_api.CbLRSessionBase.delete_registry_key
.. automethod:: cbapi.live_response_api.CbLRSessionBase.list_registry_keys_and_values
.. automethod:: cbapi.live_response_api.CbLRSessionBase.list_registry_keys

Process Operations
^^^^^^^^^^^^^^^^^^

.. automethod:: cbapi.live_response_api.CbLRSessionBase.kill_process
.. automethod:: cbapi.live_response_api.CbLRSessionBase.create_process
.. automethod:: cbapi.live_response_api.CbLRSessionBase.list_processes



