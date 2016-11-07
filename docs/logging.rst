Logging & Diagnostics
=====================

The cbapi provides extensive logging facilities to track down issues communicating with the REST API and understand
potential performance bottlenecks.

Enabling Logging
----------------

The cbapi uses Python's standard :py:mod:`logging` module for logging. To enable debug logging for the cbapi, you
can do the following::

    >>> import logging
    >>> root = logging.getLogger()
    >>> root.addHandler(logging.StreamHandler())
    >>> logging.getLogger("cbapi").setLevel(logging.DEBUG)

All REST API calls, including the API endpoint, any data sent via POST or PUT, and the time it took for the call
to complete::

    >>> user.save()
    Creating a new User object
    Sending HTTP POST /api/user with {"email": "jgarman@carbonblack.com", "first_name": "Jason", "global_admin": false, "id": null, "last_name": "Garman", "password": "cbisawesome", "teams": [], "username": "jgarman"}
    HTTP POST /api/user took 0.079s (response 200)
    Received response: {u'result': u'success'}
    HTTP GET /api/user/jgarman took 0.011s (response 200)

