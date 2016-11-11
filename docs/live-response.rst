CbAPI and Live Response
=======================

Working with the Cb Response Live Response REST API directly can be difficult. Thankfully, just like the rest of Carbon
Black's REST APIs, cbapi provides Pythonic APIs to make working with the Live Response API much easier.

In addition to easy-to-use APIs to call into Live Response, cbapi also provides a "job-based" interface that allows
cbapi to intelligently schedule Live Response

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

Live Response Errors
--------------------

There are two classes of errors that you will commonly encounter when working with the Live Response API:

* A :py:mod:`cbapi.errors.TimeoutError` is raised if a timeout is reached when