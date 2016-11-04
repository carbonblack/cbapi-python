Concepts
========

There are a few critical concepts that will make understanding and using the cbapi easier. These concepts are
explained below, and also covered in a slide deck presented at the Carbon Black regional User Exchanges in 2016.
You can see the slide deck `here <https://speakerdeck.com/cbdevnet/carbon-black-python-api-summer-2016>`_.

At a high level, the cbapi tries to represent data in Cb Response or Cb Protection as Python objects. If you've worked
with SQL Object-relational Mapping (ORM) frameworks before, then this structure may seem familiar -- cbapi was
designed to operate much like an ORM such as SQLAlchemy or Ruby's ActiveRecord. If you haven't worked with one of these
libraries, don't worry! The concepts will become clear after a little practice.

Model Objects
-------------

Everything in cbapi is represented in terms of "Model Objects". A Model Object in cbapi represents a single instance
of a specific type of data in Cb Response or Protection. For example, a process document from Cb Response (as seen
on an Analyze Process page in the Web UI) is represented as a :py:mod:`cbapi.response.models.Process` Model Object.
Similarly, a file instance in Cb Protection is represented as a  :py:mod:`cbapi.protection.models.FileInstance`
Model Object.

Once you have an instance of a Model Object, you can access all of the data contained within as Python properties.
For example, if you have a Process Model Object named ``proc`` and you want to print its command line (which is stored
in the ``cmdline`` property), you would write the code::

    >>> print(proc.cmdline)

This would automatically retrieve the ``cmdline`` attribute of the process and print it out to your screen.

The data in Cb Response and Protection may change rapidly, and so a comprehensive list of valid properties is difficult
to keep up-to-date. Therefore, if you are curious what properties are available on a specific Model Object, you can
print that Model Object to the screen. It will dump all of the available properties and their current values. For
example::

    >>> print(binary)
    cbapi.response.models.Binary:
    -> available via web UI at https://cbserver/#binary/08D1631FAF39538A133D94585644D5A8
    host_count           : 1
    digsig_result        : Signed
    observed_filename    : [u'c:\\windows\\syswow64\\appwiz.cpl']
    product_version      : 6.2.9200.16384
    legal_copyright      : © Microsoft Corporation. All rights reserved.
    digsig_sign_time     : 2012-07-26T08:56:00Z
    orig_mod_len         : 669696
    is_executable_image  : False
    is_64bit             : False
    digsig_publisher     : Microsoft Corporation
    ...

In this example, ``host_count``, ``orig_mod_len``, etc. are all properties available on this Binary Model Object.
Sometimes, properties are not available on every instance of a Model Object. In this case, you can use the ``.get()``
method to retrieve the property, and return a default value if the property does not exist on the Model Object::

    >>> print(binary.get("product_version", "<unknown>"))
    6.2.9200.16384

In summary, Model Objects contain all the data associated with a specific type of API call. In this example, the
:py:mod:`cbapi.response.models.Binary` Model Object reflects all the data available via the
``/api/v1/binary`` API route on a Cb Response server.

Joining Model Objects
---------------------

Many times, there are relationships between different Model Objects. To make navigating these relationships easy,
cbapi provides special properties to "join" Model Objects together. For example, a :py:mod:`cbapi.response.models.Process`
Model Object can reference the :py:mod:`cbapi.response.models.Sensor` or :py:mod:`cbapi.response.models.Binary`
associated with this Process.

In this case, special "join" properties are provided for you. When you use one of these properties, cbapi will
automatically retrieve the associated Model Object, if necessary.

This capability may sound like a performance killer, causing many unnecessary API calls in order to gather this data.
However, cbapi has extensive Model Object caching built-in, so multiple requests for the same data will be eliminated
and an API request is only made if the cache does not already contain the requested data.

For example, to print the name of the Sensor Group assigned to the Sensor that ran a specific Process::

    >>> print(proc.sensor.group.name)
    Default Group

Behind the scenes, this makes at most two API calls: one to obtain the Sensor associated with the Process, then another
to obtain the Sensor Group that Sensor is part of. If either the Sensor or Sensor Group are already present in cbapi's
internal cache, the respective API call is not made and the data is returned directly from the internal cache.

In summary, some Model Objects have special "join" properties that provide easy access to related Model Objects.
A list of "join" properties is included as part of the documentation for each Model Object.

Queries
-------

Now that we've covered how to get data out of a specific Model Object, we now need to learn how to obtain Model
Objects in the first place! To do this, we have to create and execute a Query. cbapi Queries use the same query
syntax accepted by Cb Response or Protection's APIs, but also add the capability to filter result sets