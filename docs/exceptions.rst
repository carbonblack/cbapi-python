.. _exceptions:

Exceptions
==========

If an error occurs, the API attempts to roll the error into an appropriate Exception class.

Exception Classes
-----------------

.. autoexception:: cbapi.errors.ApiError
.. autoexception:: cbapi.errors.CredentialError
.. autoexception:: cbapi.errors.ServerError
.. autoexception:: cbapi.errors.ObjectNotFoundError
.. autoexception:: cbapi.errors.MoreThanOneResultError
.. autoexception:: cbapi.errors.InvalidObjectError
.. autoexception:: cbapi.errors.TimeoutError
.. autoexception:: cbapi.response.live_response_api.LiveResponseError
