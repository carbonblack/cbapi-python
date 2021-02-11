CbAPI and Live Response
=======================

Working with the Live Response REST API directly can be difficult. Thankfully, just like the rest of Carbon
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

As seen in the example above, the ``.lr_session()`` method is context-aware. EDR has a limited number of
concurrent Live Response session slots (by default, only ten). By wrapping the ``.lr_session()`` call within a
``with`` context, the session is automatically closed at the end of the block and frees that slot for another
concurrent Live Response session in another script or user context.

A full listing of methods in the cbapi Live Response API is available in the documentation for
the :py:mod:`cbapi.live_response_api.CbLRSessionBase` class.

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

The basic Synchronous API described above in the Getting Started section works well for small tasks, targeting one
sensor at a time. However, if you want to execute the same set of Live Response commands across a larger number of
sensors, the cbapi provides a Job-Based Live Response API. The Job-Based Live Response API provides a straightforward
API to submit Live Response jobs to a scheduler, schedule those Live Response jobs on individual endpoints concurrently,
and return results and any errors back to you when the jobs complete. The Job-Based Live Response API is a natural
fit with the Event-Based API to create IFTTT-style pipelines; if an event is received via the Event API, then perform
Live Response actions on the affected endpoint via the Live Response Job-Based API.

The Job-Based API works by first defining a reusable "job" to perform on the endpoint. The Job is simply a class or
function that takes a Live Response session object as input and performs a series of commands. Jobs can be as simple
as retrieving a registry key, or as complex as collecting the Chrome browser history for any currently logged-in users.

Let's look at an example Job to retrieve a registry key. This example job is pulled from the ``get_reg_autoruns.py``
example script::

    class GetRegistryValue(object):
        def __init__(self, registry_key):
            self.registry_key = registry_key

        def run(self, session):
            reg_info = session.get_registry_value(self.registry_key)
            return time.time(), session.sensor_id, self.registry_key, reg_info["value_data"]

To submit this job, you instantiate an instance of a ``GetRegistryValue`` class with the registry key you want to pull
back from the endpoint, and submit the ``.run()`` method to the Live Response Job API::

    >>> job = GetRegistryValue(regmod_path)
    >>> registry_job = cb.live_response.submit_job(job.run, sensor_id)

Your script resumes execution immediately after the call to ``.submit_job()``. The job(s) that you've submitted will
be executed in a set of background threads managed by cbapi.

