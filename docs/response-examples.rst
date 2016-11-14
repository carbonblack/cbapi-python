Cb Response API Examples
========================

Now that we've covered the basics, let's step through a few examples using the Cb Response API. In these examples,
we will assume the following boilerplate code to enable logging and establish a connection to the "default"
Cb Response server in our credential file::

    >>> import logging
    >>> root = logging.getLogger()
    >>> root.addHandler(logging.StreamHandler())
    >>> logging.getLogger("cbapi").setLevel(logging.DEBUG)

    >>> from cbapi.response import *
    >>> cb = CbResponseAPI()

With that boilerplate out of the way, let's take a look at a few examples.

Download a Binary from Cb Response
----------------------------------

Let's grab a binary that Cb Response has collected from one of the endpoints. This can be useful if you want to
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
    >>> bh.save()
    Creating a new BannedHash object
    Sending HTTP POST /api/v1/banning/blacklist with {"md5hash": "7FB55F5A62E78AF9B58D08AAEEAEF848", "text": "banned from API"}
    HTTP POST /api/v1/banning/blacklist took 0.035s (response 200)
    Received response: {u'result': u'success'}
    HTTP GET /api/v1/banning/blacklist/7FB55F5A62E78AF9B58D08AAEEAEF848 took 0.039s (response 200)

Note that if the hash is already banned in Cb Response, then you will receive a `ServerError` exception with the message that
the banned hash already exists.

Isolate a Sensor
----------------

Switching gears, let's take a Sensor and quarantine it from the network. The Cb Response network isolation
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

The ``.isolate()`` method will keep polling the Cb Response server until the sensor has confirmed that it is now
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

Now, let's do some queries into the Cb Response database. The true power of Cb Response is its continuous recording
and powerful query language that allows you to go back in time and track the root cause of any security incident on
your endpoints. Let's start with a simple query to find instances of a specific behavioral IOC, where our attacker
used the built-in Windows tool ``net.exe`` to mount an internal network share. We will iterate over all uses
of ``net.exe`` to mount our target share, printing out the parent processes that led to the execution of the offending
command::

    >>> query = cb.select(Process).where("process_name:net.exe").and_(r"cmdline:\\test\blah")
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
of all parent processes.
