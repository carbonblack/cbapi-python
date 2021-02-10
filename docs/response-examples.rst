VMware Carbon Black EDR Examples
================================

Now that we've covered the basics, let's step through a few examples using the EDR API. In these examples,
we will assume the following boilerplate code to enable logging and establish a connection to the "default"
EDR server in our credential file::

    >>> import logging
    >>> root = logging.getLogger()
    >>> root.addHandler(logging.StreamHandler())
    >>> logging.getLogger("cbapi").setLevel(logging.DEBUG)

    >>> from cbapi.response import *
    >>> cb = CbResponseAPI()

With that boilerplate out of the way, let's take a look at a few examples.

Download a Binary from EDR
--------------------------

Let's grab a binary that EDR has collected from one of the endpoints. This can be useful if you want to
send this binary for further automated analysis or pull it down for manual reverse engineering. You can see a full
example with command line options in the examples directory: ``binary_download.py``.

Let's step through the example::

    >>> import shutil
    >>> md5 = "7FB55F5A62E78AF9B58D08AAEEAEF848"
    >>> binary = cb.select(Binary, md5)
    >>> shutil.copyfileobj(binary.file, open(binary.original_filename, "wb"))

First, we select the binary by its primary key: the MD5 hash of the binary contents. The third line requests the
binary file data by accessing the ``file`` property on the Binary Model Object. The ``file`` property acts as a
read-only, Python file-like object.
In this case, we use the Python ``shutil`` library to copy one file object to another. The
advantage of using ``shutil`` is that the file is copied in chunks, and the full file does not have to be read
into memory before saving it to disk.

Another way to use the ``file`` property is to call ``.read()`` on it just like any other Python file object. The
following code will read the first two bytes from the Binary::

    >> binary.file.read(2)
    "MZ"

Ban a Binary
------------

Now let's take this binary and add a Banning rule for it. To do this, we create a new BannedHash Model Object::

    >>> bh = cb.create(BannedHash)
    >>> bh.md5hash = binary.md5
    >>> bh.text = "Banned from API"
    >>> bh.enabled = True
    >>> bh.save()
    Creating a new BannedHash object
    Sending HTTP POST /api/v1/banning/blacklist with {"md5hash": "7FB55F5A62E78AF9B58D08AAEEAEF848", "text": "banned from API"}
    HTTP POST /api/v1/banning/blacklist took 0.035s (response 200)
    Received response: {u'result': u'success'}
    HTTP GET /api/v1/banning/blacklist/7FB55F5A62E78AF9B58D08AAEEAEF848 took 0.039s (response 200)

Note that if the hash is already banned in EDR, then you will receive a `ServerError` exception with the message that
the banned hash already exists.

Isolate a Sensor
----------------

Switching gears, let's take a Sensor and quarantine it from the network. The EDR network isolation
functionality allows administrators to isolate endpoints that may be actively involved in an incident, while preserving
access to perform Live Response on that endpoint and collect further endpoint telemetry.

To isolate a sensor, we first need to acquire its Sensor Model Object::

    >>> sensor = cb.select(Sensor).where("hostname:HOSTNAME").first()

This will select the first sensor that matches the hostname ``HOSTNAME``. Now we can isolate that machine::

    >>> sensor.isolate()
    Updating Sensor with unique ID 4
    Sending HTTP PUT /api/v1/sensor/4 with {"boot_id": "0", "build_id": 5, "build_version_string": "005.002.000.61003", ...}
    HTTP PUT /api/v1/sensor/4 took 0.129s (response 204)
    HTTP GET /api/v1/sensor/4 took 0.050s (response 200)
    ...
    True

The ``.isolate()`` method will keep polling the EDR server until the sensor has confirmed that it is now
isolated from the network. If the sensor is offline or otherwise unreachable, this call could never return. Therefore,
there is also a ``timeout=`` keyword parameter that can be used to set an optional timeout that, if reached,
will throw a ``TimeoutError`` exception. The ``.isolate()`` function returns True when the sensor is successfully
isolated.

When you're ready to restore full network connectivity to the sensor, simply call the ``.unisolate()`` method::

    >>> sensor.unisolate()
    Updating Sensor with unique ID 4
    Sending HTTP PUT /api/v1/sensor/4 with {"boot_id": "0", "build_id": 5, "build_version_string": "005.002.000.61003", ...}
    HTTP PUT /api/v1/sensor/4 took 0.077s (response 204)
    HTTP GET /api/v1/sensor/4 took 0.020s (response 200)
    ...
    True

Again, once the sensor is back on the network, the ``.unisolate()`` method will return True. Just like ``.isolate()``,
you can optionally specify a timeout using the ``timeout=`` keyword parameter.

Querying Processes and Events
-----------------------------

Now, let's do some queries into the EDR database. The true power of EDR is its continuous recording
and powerful query language that allows you to go back in time and track the root cause of any security incident on
your endpoints. Let's start with a simple query to find instances of a specific behavioral IOC, where our attacker
used the built-in Windows tool ``net.exe`` to mount an internal network share. We will iterate over all uses
of ``net.exe`` to mount our target share, printing out the parent processes that led to the execution of the offending
command::

    >>> query = cb.select(Process).where("process_name:net.exe").and_(r"cmdline:\\test\blah").group_by("id")
    >>> def print_details(proc, depth):
    ...     print("%s%s: %s ran %s" % (" "*depth, proc.start, proc.username, proc.cmdline))
    ...
    >>> for proc in query:
    ...     print_details(proc, 0)
    ...     proc.walk_parents(print_details)
    ...
    HTTP GET /api/v1/process?cb.urlver=1&facet=false&q=process_name%3Anet.exe+cmdline%3A%5C%5Ctest%5Cblah&rows=100&sort=last_update+desc&start=0 took 0.462s (response 200)
    2016-11-11 20:59:31.631000: WIN-IA9NQ1GN8OI\bit9rad ran net  use y: \\test\blah
    HTTP GET /api/v3/process/00000003-0000-036c-01d2-2efd3af51186/1/event took 0.036s (response 200)
    2016-10-25 20:20:29.790000: WIN-IA9NQ1GN8OI\bit9rad ran "C:\Windows\system32\cmd.exe"
    HTTP GET /api/v3/process/00000003-0000-0c34-01d2-2ec94f09cae6/1/event took 0.213s (response 200)
     2016-10-25 14:08:49.651000: WIN-IA9NQ1GN8OI\bit9rad ran C:\Windows\Explorer.EXE
    HTTP GET /api/v3/process/00000003-0000-0618-01d2-2ec94edef208/1/event took 0.013s (response 200)
      2016-10-25 14:08:49.370000: WIN-IA9NQ1GN8OI\bit9rad ran C:\Windows\system32\userinit.exe
    HTTP GET /api/v3/process/00000003-0000-02ec-01d2-2ec9412b4b70/1/event took 0.017s (response 200)
       2016-10-25 14:08:26.382000: SYSTEM ran winlogon.exe
    HTTP GET /api/v3/process/00000003-0000-02b0-01d2-2ec94115df7a/1/event took 0.012s (response 200)
        2016-10-25 14:08:26.242000: SYSTEM ran \SystemRoot\System32\smss.exe 00000001 00000030
    HTTP GET /api/v3/process/00000003-0000-0218-01d2-2ec93f813429/1/event took 0.021s (response 200)
         2016-10-25 14:08:23.590000: SYSTEM ran \SystemRoot\System32\smss.exe
    HTTP GET /api/v3/process/00000003-0000-0004-01d2-2ec93f7c7181/1/event took 0.081s (response 200)
          2016-10-25 14:08:23.559000: SYSTEM ran c:\windows\system32\ntoskrnl.exe
    HTTP GET /api/v3/process/00000003-0000-0000-01d2-2ec93f6051ee/1/event took 0.011s (response 200)
           2016-10-25 14:08:23.374000:  ran c:\windows\system32\ntoskrnl.exe
    HTTP GET /api/v3/process/00000003-0000-0004-01d2-2ec93f6051ee/1/event took 0.011s (response 200)
    2016-11-11 20:59:25.667000: WIN-IA9NQ1GN8OI\bit9rad ran net  use z: \\test\blah
    2016-10-25 20:20:29.790000: WIN-IA9NQ1GN8OI\bit9rad ran "C:\Windows\system32\cmd.exe"
     2016-10-25 14:08:49.651000: WIN-IA9NQ1GN8OI\bit9rad ran C:\Windows\Explorer.EXE
      2016-10-25 14:08:49.370000: WIN-IA9NQ1GN8OI\bit9rad ran C:\Windows\system32\userinit.exe
       2016-10-25 14:08:26.382000: SYSTEM ran winlogon.exe
        2016-10-25 14:08:26.242000: SYSTEM ran \SystemRoot\System32\smss.exe 00000001 00000030
         2016-10-25 14:08:23.590000: SYSTEM ran \SystemRoot\System32\smss.exe
          2016-10-25 14:08:23.559000: SYSTEM ran c:\windows\system32\ntoskrnl.exe
           2016-10-25 14:08:23.374000:  ran c:\windows\system32\ntoskrnl.exe

That was a lot in one code sample, so let's break it down part-by-part.

First, we set up the ``query`` variable by creating a new ``Query`` object using the ``.where()`` and ``.and_()``
methods. Next, we define a function that will get called on each parent process all the way up the chain to the system
kernel loading during the boot process. This function, ``print_details``, will print a few data points about each
process: namely, the local endpoint time when that process started, the user who spawned the process, and the
command line for the process.

Finally, we execute our query by looping over the result set with a Python for loop. For each process that matches
the query, first we print details of the process itself (the process that called ``net.exe`` with a command line
argument of our target share ``\\test\blah``), then calls the ``.walk_parents()`` helper method to walk up the chain
of all parent processes. Each level of parent process (the "depth") is represented by an extra space; therefore, reading
backwards, you can see that ``ntoskrnl.exe`` spawned ``smss.exe``, which in turn spawned ``winlogon.exe``, and so on.
You can see the full backwards chain of events that ultimately led to the execution of each of these ``net.exe`` calls.

Remember that we have logging turned on for these examples, so you see each of the HTTP GET requests to retrieve process
event details as they happen. Astute observers will note that walking the parents of the second ``net.exe`` command,
where the ``\\test\blah`` share was mounted on the ``z:`` drive, did not trigger additional HTTP GET requests. This
is thanks to cbapi's caching layer. Since both ``net.exe`` commands ran as part of the same command shell session, the
parent processes are shared between the two executions. Since the parent processes were already requested as part of
the previous walk up the chain of parent processes, cbapi did not re-request the data from the server, instead using its
internal cache to satisfy the process information requests from this script.

New Filters: Group By, Time Restrictions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the query above, there is an extra ``.group_by()`` method. This method is new in cbapi 1.1.0 and is part of five
new query filters available when communicating with an EDR 6.1 server. These filters are accessible via methods
on the ``Process`` Query object. These new methods are:

* ``.group_by()`` - Group the result set by a field in the response. Typically you will want to group by ``id``, which
  will ensure that the result set only has one result per *process* rather than one result per *event segment*. For
  more information on processes, process segments, and how segments are stored in EDR 6.0, see the
  `Process API Changes for EDR 6.0 <https://developer.carbonblack.com/reference/enterprise-response/6.1/process-api-changes/>`_
  page on the Developer Network website.
* ``.min_last_update()`` - Only return processes that have events after a given date/time stamp (relative to the
  individual sensor's clock)
* ``.max_last_update()`` - Only return processes that have events before a given date/time stamp (relative to the
  individual sensor's clock)
* ``.min_last_server_update()`` - Only return processes that have events after a given date/time stamp (relative to the
  EDR server's clock)
* ``.max_last_server_update()`` - Only return processes that have events before a given date/time stamp (relative to the
  EDR server's clock)

EDR 6.1 uses a new way of recording process events that greatly increases the speed and scale of collection,
allowing you to store and search data for more endpoints on the same hardware. Details on the new database format
can be found on the Developer Network website at the `Process API Changes for EDR 6.0
<https://developer.carbonblack.com/reference/enterprise-response/6.1/process-api-changes/>`_ page.

The ``Process`` Model Object traditionally referred to a single "segment" of events in the EDR database. In
EDR versions prior to 6.0, a single segment will include up to 10,000 individual endpoint events, enough to
handle over 95% of the typical event activity for a given process. Therefore, even though a ``Process`` Model Object
technically refers to a single *segment* in a process, since most processes had less than 10,000 events and therefore
were only comprised of a single segment, this distinction wasn't necessary.

However, now that processes are split across many segments, a better way of handling this is necessary. Therefore,
EDR 6.0 introduces the new ``.group_by()`` method.

More on Filters
~~~~~~~~~~~~~~~

Querying for a process will return *all* segments that match. For example, if you search for ``process_name:cmd.exe``,
the result set will include *all* segments of *all* ``cmd.exe`` processes. Therefore, EDR 6.1 introduced
the ability to "group" result sets by a field in the result. Typically you will want to group by the internal process
id (the ``id`` field), and this is what we did in the query above. Grouping by the ``id`` field will ensure that only
one result is returned per *process* rather than per *segment*.

Let's take a look at an example::

    >>> from datetime import datetime, timedelta
    >>> yesterday = datetime.utcnow() - timedelta(days=1)      # Get "yesterday" in GMT
    >>> for proc in c.select(Process).where("process_name:cmd.exe").min_last_update(yesterday):
    ...     print proc.id, proc.segment
    DEBUG:cbapi.connection:HTTP GET /api/v1/process?cb.min_last_update=2017-05-21T18%3A41%3A58Z&cb.urlver=1&facet=false&q=process_name%3Acmd.exe&rows=100&sort=last_update+desc&start=0 took 2.164s (response 200)
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495465643405
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495465407157
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495463680155
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495463807694
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495463543944
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495463176570
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495463243492

Notice that the "same" process ID is returned seven times, but with seven different segment IDs. EDR will
return *every* process event segment that matches a given query, in this case, any event segment that contains the
process command name ``cmd.exe``.

That is, however, most likely not what you wanted. Instead, you'd like a list of the *unique* processes associated with
the command name ``cmd.exe``. Just add the ``.group_by("id")`` filter to your query::

    >>> for proc in c.select(Process).where("process_name:cmd.exe").min_last_update(yesterday).group_by("id"):
    ...     print proc.id, proc.segment
    DEBUG:cbapi.connection:HTTP GET /api/v1/process?cb.group=id&cb.min_last_update=2017-05-21T18%3A41%3A58Z&cb.urlver=1&facet=false&q=process_name%3Acmd.exe&rows=100&sort=last_update+desc&start=0 took 2.163s (response 200)
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495465643405


Feed and Watchlist Maintenance
------------------------------

The cbapi provides several helper functions to assist in creating watchlists and feeds.

Watchlists are simply saved Queries that are automatically run on the EDR server on a periodic basis. Results
of the watchlist are tagged in the database and optionally trigger alerts. Therefore, a cbapi Query can easily be
converted into a watchlist through the Query ``.create_watchlist()`` function::

    >>> new_watchlist = query.create_watchlist("[WARN] Attempts to mount internal share")
    Creating a new Watchlist object
    Sending HTTP POST /api/v1/watchlist with {"id": null, "index_type": "events", "name": "[WARN] Attempts to mount internal share", "search_query": "facet=false&q=process_name%3Anet.exe+cmdline%3A%5C%5Ctest%5Cblah&cb.urlver=1&sort=last_update+desc"}
    HTTP POST /api/v1/watchlist took 0.510s (response 200)
    Received response: {u'id': 222}
    Only received an ID back from the server, forcing a refresh
    HTTP GET /api/v1/watchlist/222 took 0.034s (response 200)

This helper function will automatically create a watchlist from the Query object with the given name.

If you have a watchlist that already exists, the Watchlist Model Object can help you extract the human-readable
query from the watchlist. Just select the watchlist and access the ``.query`` property on the Watchlist Model Object::

    >>> my_watchlist = cb.select(Watchlist).where("name:[WARN] Attempts to mount internal share").one()
    >>> print(my_watchlist.query)
    process_name:net.exe cmdline:\\test\blah

You can also execute the query straight from the Watchlist Model Object::

    >>> len(my_watchlist.search())
    HTTP GET /api/v1/process?cb.urlver=1&facet=false&q=process_name%3Anet.exe+cmdline%3A%5C%5Ctest%5Cblah&rows=0&start=0 took 0.477s (response 200)
    2

And finally, you can of course enable and disable Watchlists::

    >>> my_watchlist.enabled = False
    >>> my_watchlist.save()
    Updating Watchlist with unique ID 222
    Sending HTTP PUT /api/v1/watchlist/222 with {"alliance_id": null, "date_added": "2016-11-15 23:48:27.615993-05:00", "enabled": false, "from_alliance": false, "group_id": -1, "id": "222", "index_type": "events", "last_hit": "2016-11-15 23:50:08.448685-05:00", "last_hit_count": 2, "name": "[WARN] Attempts to mount internal share", "readonly": false, "search_query": "facet=false&q=process_name%3Anet.exe%20cmdline%3A%5C%5Ctest%5Cblah&cb.urlver=1", "search_timestamp": "2016-11-16T04:50:01.750240Z", "total_hits": "2", "total_tags": "2"}
    HTTP PUT /api/v1/watchlist/222 took 0.036s (response 200)
    Received response: {u'result': u'success'}
    HTTP GET /api/v1/watchlist/222 took 0.029s (response 200)

You can see more examples of Feed and Watchlist maintenance in the ``feed_operations.py`` and ``watchlist_operations.py``
example scripts.

Managing Threat Reports & Alerts
--------------------------------

The cbapi provides helper functions to manage alerts and threat reports in bulk. The Query objects associated with
the ThreatReport and Alert Model Objects provide a few bulk operations to help manage large numbers of Threat Reports
and Alerts, respectively.

To mark a large number of Threat Reports as false positives, create a query that matches the Reports you're
interested in.  For example, if every Report from the Feed named "SOC" that contains the word "FUZZYWOMBAT" in the
report title should be considered a false positive (and no longer trigger Alerts), you can write the following code
to do so::

    >>> feed = c.select(Feed).where("name:SOC").one()
    >>> report_query = feed.reports.where("title:FUZZYWOMBAT")
    >>> report_query.set_ignored()

Similar actions can be taken on Alerts. The AlertQuery object exposes three helper methods to perform bulk operations
on sets of Alerts: ``.set_ignored()``, ``.assign_to()``, and ``.change_status()``.


Joining Everything Together
---------------------------

Now that we've examined how to request information on binaries, sensors, and processes through cbapi, let's chain
this all together using the "join" functionality of cbapi's Model Objects. Let's just tweak the ``print_details``
function from above to add a few more contextual details. Our new function will now include the following data points
for each process:

* The hostname the process was executed on
* The sensor group that host belongs to
* If the binary was signed, also print out:
    * The number of days between when the binary was signed and it was executed on the endpoint
    * The verified publisher name from the digital signature

We can transparently "join" between the Process Model Object and the Sensor, Sensor Group, and Binary Model Objects
using the appropriately named helper properties. Here's the new function::

    >>> import pytz

    >>> def print_details(proc, depth):
    ...     print("On host {0} (part of sensor group {1}):".format(proc.hostname, proc.sensor.group.name))
    ...     print("- At {0}, process {1} was executed by {2}".format(proc.start, proc.cmdline, proc.username))
    ...     if proc.binary.signed:
    ...         # force local timestamp into UTC, we're just looking for an estimate here.
    ...         utc_timestamp = proc.start.replace(tzinfo=pytz.timezone("UTC"))
    ...         days_since_signed = (utc_timestamp - proc.binary.signing_data.sign_time).days
    ...         print("- That binary ({0}) was signed by {1} {2} days before it was executed.".format(proc.process_md5,
    ...             proc.binary.signing_data.publisher, days_since_signed))

Now if we run our for loop from above again::

    >>> for proc in query:
    ...     print_details(proc, 0)
    ...     proc.walk_parents(print_details)
    ...
    HTTP GET /api/v1/process?cb.urlver=1&facet=false&q=process_name%3Anet.exe+cmdline%3A%5C%5Ctest%5Cblah&rows=100&sort=last_update+desc&start=0 took 0.487s (response 200)
    HTTP GET /api/v1/sensor/3 took 0.037s (response 200)
    HTTP GET /api/group/1 took 0.022s (response 200)
    On host WIN-IA9NQ1GN8OI (part of sensor group Default Group):
    - At 2016-11-11 20:59:31.631000, process net  use y: \\test\blah was executed by WIN-IA9NQ1GN8OI\bit9rad
    HTTP GET /api/v1/binary/79B6D4C5283FC806387C55B8D7C8B762/summary took 0.016s (response 200)
    - That binary (79b6d4c5283fc806387c55b8d7c8b762) was signed by Microsoft Corporation 1569 days before it was executed.
    HTTP GET /api/v3/process/00000003-0000-036c-01d2-2efd3af51186/1/event took 0.045s (response 200)
    On host WIN-IA9NQ1GN8OI (part of sensor group Default Group):
    - At 2016-10-25 20:20:29.790000, process "C:\Windows\system32\cmd.exe"  was executed by WIN-IA9NQ1GN8OI\bit9rad
    HTTP GET /api/v1/binary/BF93A2F9901E9B3DFCA8A7982F4A9868/summary took 0.015s (response 200)
    - That binary (bf93a2f9901e9b3dfca8a7982f4a9868) was signed by Microsoft Corporation 1552 days before it was executed.

Those few lines of Python above are jam-packed with functionality. Now for each process execution, we have added
contextual information on the source host, the group that host is part of, and details about the signing status of the
binary that was executed. The magic is performed behind the scenes when we use the ``.binary`` and ``.sensor`` properties
on the Process Model Object. Just like our previous example, cbapi's caching layer ensures that we do not overload
the EDR server with duplicate requests for the same data. In this example, multiple redundant requests for sensor,
sensor group, and binary data are all eliminated by cbapi's cache.

Facets
------

The cbapi also provides functionality to pull facet information from the database. You can use the ``.facet()`` method
on a Query object to retrieve facet (ie. "group") information for a given query result set. Here's an example that
pulls the most common process names for our sample host::

    >>> def print_facet_histogram(facets):
    ...     for entry in facets:
    ...         print("%15s: %5s%% %s" % (entry["name"][:15], entry["ratio"], u"\u25A0"*(int(entry["percent"])/2)))
    ...

    >>> facet_query = cb.select(Process).where("hostname:WIN-IA9NQ1GN8OI").and_("username:bit9rad")
    >>> print_facet_histogram(facet_query.facets("process_name")["process_name"])

    HTTP GET /api/v1/process?cb.urlver=1&facet=true&facet.field=process_name&facet.field=username&q=hostname%3AWIN-IA9NQ1GN8OI+username%3Abit9rad&rows=0&start=0 took 0.024s (response 200)
         chrome.exe:  23.4% ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
    thumbnailextrac:  15.4% ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
       adobearm.exe:   8.6% ■■■■■■■■■■■■■■■■■■
       taskhost.exe:   6.0% ■■■■■■■■■■■■
        conhost.exe:   4.7% ■■■■■■■■■
           ping.exe:   4.0% ■■■■■■■■
         wermgr.exe:   3.5% ■■■■■■■

In the above example, we just pulled one facet: the ``process_name``; you can ask the server for faceting on multiple
fields in one query by simply listing the fields in the call to ``.facet()``: for example, ``.facet("username", "process_name")``
will produce a dictionary with two top-level keys: ``username`` and ``process_name``.

Administrative Tasks
--------------------

In addition to querying data, you can also perform various administrative tasks using cbapi.

Let's create a user on our EDR server::

    >>> user = cb.create(User)
    >>> user.username = "jgarman"
    >>> user.password = "cbisawesome"
    >>> user.first_name = "Jason"
    >>> user.last_name = "Garman"
    >>> user.email = "jgarman@carbonblack.com"
    >>> user.teams = []
    >>> user.global_admin = False
    Creating a new User object
    Sending HTTP POST /api/user with {"email": "jgarman@carbonblack.com", "first_name": "Jason", "global_admin": false, "id": null, "last_name": "Garman", "password": "cbisawesome", "teams": [], "username": null}
    HTTP POST /api/user took 0.608s (response 200)
    Received response: {u'result': u'success'}

How about moving a sensor to a new Sensor Group::

    >>> sg = cb.create(SensorGroup)
    >>> sg.name = "Critical Endpoints"
    >>> sg.site = 1
    >>> sg.save()
    Creating a new SensorGroup object
    Sending HTTP POST /api/group with {"id": null, "name": "Critical Endpoints", "site_id": 1}
    HTTP POST /api/group took 0.282s (response 200)
    Received response: {u'id': 2}
    Only received an ID back from the server, forcing a refresh
    HTTP GET /api/group/2 took 0.011s (response 200)
    >>> sensor = cb.select(Sensor).where("hostname:WIN-IA9NQ1GN8OI").first()
    >>> sensor.group = sg
    >>> sensor.save()
    Updating Sensor with unique ID 3
    Sending HTTP PUT /api/v1/sensor/3 with {"boot_id": "2", "build_id": 2, "build_version_string": "005.002.000.60922", ...
    HTTP PUT /api/v1/sensor/3 took 0.087s (response 204)
    HTTP GET /api/v1/sensor/3 took 0.030s (response 200)

