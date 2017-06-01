.. _response_api:

Cb Response API
===============

This page documents the public interfaces exposed by cbapi when communicating with a Carbon Black Enterprise
Response server.

Main Interface
--------------

To use cbapi with Carbon Black Response, you will be using the CbResponseAPI.
The CbResponseAPI object then exposes two main methods to select data on the Carbon Black server:

.. autoclass:: cbapi.response.rest_api.CbResponseAPI
    :members:

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

.. autoclass:: cbapi.response.live_response_api.LiveResponseSession

File Operations
^^^^^^^^^^^^^^^

.. automethod:: cbapi.response.live_response_api.LiveResponseSession.get_file
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.delete_file
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.put_file
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.list_directory
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.create_directory
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.walk

Registry Operations
^^^^^^^^^^^^^^^^^^^

.. automethod:: cbapi.response.live_response_api.LiveResponseSession.get_registry_value
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.set_registry_value
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.delete_registry_value
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.create_registry_key
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.delete_registry_key
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.list_registry_keys_and_values
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.list_registry_keys

Process Operations
^^^^^^^^^^^^^^^^^^

.. automethod:: cbapi.response.live_response_api.LiveResponseSession.kill_process
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.create_process
.. automethod:: cbapi.response.live_response_api.LiveResponseSession.list_processes



