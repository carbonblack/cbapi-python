CbAPI and Live Response
=======================

Working with the Cb Response Live Response REST API directly can be difficult. Thankfully, just like the rest of Carbon
Black's REST APIs, cbapi provides Pythonic APIs to make working with the Live Response API much easier.

In addition to easy-to-use APIs to call into Live Response, cbapi also provides a "job-based" interface that allows
cbapi to intelligently schedule large numbers of concurrent Live Response sessions across multiple sensors. Your code
can then be notified when the jobs are complete, returning the results of the job if it succeeded or the Exception
if it failed.

Getting Started with Live Response
----------------------------------

The cbapi Live Response API is built around establishing a
:py:mod:`cbapi.response.live_response.LiveResponseSession` object from a :py:mod:`cbapi.response.models.Sensor` Model
Object. Then you can call methods on the ``LiveResponseSession`` object to perform Live Response actions on the
target host. These calls are synchronous, meaning that they will wait until the action is complete and a result is
available, before returning back to your script. Here's an example::

    >>> from cbapi.response import *
    >>> cb = CbResponseAPI()
    >>> sensor = cb.select(Sensor).where("hostname:WIN-IA9NQ1GN8OI").first()
    >>> with sensor.lr_session() as session:
    ...     print(session.get_file(r"c:\test.txt"))

    this is a test

Since the Live Response API is synchronous, the script will not continue until either the Live Response session is
established and the file contents are retrieved, or an exception occurs (in this case, either a timeout error or
an error reading the file).

As seen in the example above, the ``.lr_session()`` method is context-aware. Cb Response has a limited number of
concurrent Live Response session slots (by default, only ten). By wrapping the ``.lr_session()``

A full listing of methods in the cbapi Live Response API is available in the documentation for
the :py:mod:`cbapi.response.live_response_api.LiveResponseSession` class.

Live Response Errors
--------------------

There are four classes of errors that you will commonly encounter when working with the Live Response API:

* A :py:mod:`cbapi.errors.TimeoutError` is raised if a timeout is encountered when waiting for a response for a
  Live Response API request.

* A :py:mod:`cbapi.response.live_response_api.LiveResponseError` is raised if an error is returned during the
  execution of a Live Response command on an endpoint. The ``LiveResponseError`` includes detailed information
  about the error that occurred, including the exact error code that was returned from the endpoint and a textual
  description of the error.

* A :py:mod:`cbapi.errors.ApiError` is raised if you attempt to execute a command that is not supported by the sensor;
  for example, attempting to acquire a memory dump from a sensor running a pre-5.1 version of the agent will fail with
  an ``ApiError`` exception.

* A :py:mod:`cbapi.errors.ServerError` is raised if any other error occurs; for example, a 500 Internal Server Error is
  returned from the Live Response API.

Job-Based API
-------------

The basic synchronous API described above in the Getting Started section works well for small tasks, targeting one
sensor at a time. However, if you want to execute the same set of Live Response commands across a larger number of
sensors