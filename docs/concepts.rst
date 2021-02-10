Concepts
========

There are a few critical concepts that will make understanding and using the cbapi easier. These concepts are
explained below, and also covered in a slide deck presented at the Carbon Black regional User Exchanges in 2016.
You can see the slide deck `here <https://speakerdeck.com/cbdevnet/carbon-black-python-api-summer-2016>`_.

At a high level, the cbapi tries to represent data in EDR or App Control as Python objects. If you've worked
with SQL Object-relational Mapping (ORM) frameworks before, then this structure may seem familiar -- cbapi was
designed to operate much like an ORM such as SQLAlchemy or Ruby's ActiveRecord. If you haven't worked with one of these
libraries, don't worry! The concepts will become clear after a little practice.

Model Objects
-------------

Everything in cbapi is represented in terms of "Model Objects". A Model Object in cbapi represents a single instance
of a specific type of data in EDR or App Control. For example, a process document from EDR (as seen
on an Analyze Process page in the Web UI) is represented as a :py:mod:`cbapi.response.models.Process` Model Object.
Similarly, a file instance in App Control is represented as a  :py:mod:`cbapi.protection.models.FileInstance`
Model Object.

Once you have an instance of a Model Object, you can access all of the data contained within as Python properties.
For example, if you have a Process Model Object named ``proc`` and you want to print its command line (which is stored
in the ``cmdline`` property), you would write the code::

    >>> print(proc.cmdline)

This would automatically retrieve the ``cmdline`` attribute of the process and print it out to your screen.

The data in EDR and App Control may change rapidly, and so a comprehensive list of valid properties is difficult
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
``/api/v1/binary`` API route on an EDR server.

Joining Model Objects
---------------------

Many times, there are relationships between different Model Objects. To make navigating these relationships easy,
cbapi provides special properties to "join" Model Objects together. For example, a
:py:mod:`cbapi.response.models.Process` Model Object can reference the :py:mod:`cbapi.response.models.Sensor` or
:py:mod:`cbapi.response.models.Binary` associated with this Process.

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
syntax accepted by EDR or App Control's APIs, and add a few little helpful features along the way.

To create a query in cbapi, use the ``.select()`` method on the CbResponseAPI or CbProtectionAPI object. Pass the
Model Object type as a parameter to the ``.select()`` call and optionally add filtering criteria with ``.where()``
clauses.

Let's start with a simple query for EDR::

    >>> from cbapi.response import *
    >>> cb = CbResponseAPI()
    >>> cb.select(Process).where("process_name:cmd.exe")
    <cbapi.response.rest_api.Query object at 0x1068815d0>

This returns a prepared Query object with the query string ``process_name:cmd.exe``.
Note that at this point no API calls have been made. The cbapi Query objects are "lazy" in that they are only
evaluated when you use them. If you create a Query object but never attempt to retrieve any results, no API call is
ever made (I suppose that answers the age-old question; if a Query object is created, but nobody uses it, it does
not make a sound, after all).

What can we do with a Query? The first thing we can do is compose new Queries. Most Query types in cbapi can be
"composed"; that is, you can create a new query from more than one query string. This can be useful if you have a
"base" query and want to add additional filtering criteria. For example, if we take the query above and add the
additional filtering criteria ``(filemod:*.exe or filemod:*.dll)``, we can write::

    >>> base_query = cb.select(Process).where("process_name:cmd.exe")
    >>> composed_query = base_query.where("(filemod:*.exe or filemod:*.dll")

Now the ``composed_query`` is equivalent to a query of ``process_name:cmd.exe (filemod:*.exe or filemod:*.dll)``.
You can also add sorting criteria to a query::

    >>> sorted_query = composed_query.sort("last_update asc")

Now when we execute the ``sorted_query``, the results will be sorted by the last server update time in ascending order.

Ok, now we're ready to actually execute a query and retrieve the results. You can think of a Query as a kind of
"infinite" Python list. Generally speaking, you can use all the familiar ways to access a Python list to access the
results of a cbapi query. For example::

    >>> len(base_query)    # How many results were returned for the query?
    3

    >>> base_query[:2]     # I want the first two results
    [<cbapi.response.models.Process: id 00000003-0000-036c-01d2-2efd3af51186-00000001> @ https://cbserver,
    <cbapi.response.models.Process: id 00000003-0000-07d4-01d2-2efcd4949dfc-00000001> @ https://cbserver]

    >>> base_query[-1:]    # I want the last result
    [<cbapi.response.models.Process: id 00000002-0000-0f2c-01d2-2a57625ca0dd-00000001> @ https://cbserver]

    >>> for proc in base_query:  # Loop over all the results
    >>>     print(proc.cmdline)
    "C:\Windows\system32\cmd.exe"
    "C:\Windows\system32\cmd.exe"
    "C:\Windows\system32\cmd.exe"

    >>> procs = list(base_query) # Just make a list of all the results

In addition to using a Query object as an array, two helper methods are provided as common shortcuts. The first
method is ``.one()``. The ``.one()`` method is useful when you know only one result should match your query; it
will throw a :py:mod:`MoreThanOneResultError` exception if there are zero or more than one results for the query. The
second method is ``.first()``, which will return the first result from the result set, or None if there are no results.

Every time you access a Query object, it will perform a REST API query to the Carbon Black server. For large result
sets, the results are retrieved in batches- by default, 100 results per API request on EDR and 1,000 results
per API request on App Control. The search queries themselves are not cached, but the resulting Model Objects are.

Retrieving Objects by ID
------------------------

Every Model Object (and in fact any object addressable via the REST API) has a unique ID associated with it. If you
already have a unique ID for a given Model Object, for example, a Process GUID for EDR, or a Computer ID
for App Control, you can ask cbapi to give you the associated Model Object for that ID by passing that ID to the
``.select()`` call. For example::

    >>> binary = cb.select(Binary, "CA4FAFFA957C71C006B59E29DFE3EB8B")
    >>> print(binary.file_desc)
    PNRP Name Space Provider

Note that retrieving an object via ``.select()`` with the ID does not automatically request the object from the server
via the API. If the Model Object is already in the local cache, the locally cached version is returned. If it is not,
a "blank" Model Object is created and is initialized only when an attempt is made to read a property. Therefore,
assuming an empty cache, in the example above, the REST API query would not happen until the second line
(the ``print`` statement). If you want to ensure that an object exists at the time you call ``.select()``, add the
``force_init=True`` keyword parameter to the ``.select()`` call. This will cause cbapi to force a refresh of the
object and if it does not exist, cbapi will throw a :py:mod:`ObjectNotFoundError` exception.

Creating New Objects
--------------------

The EDR and App Control REST APIs provide the ability to insert new data under certain circumstances. For
example, the EDR REST API allows you to insert a new banned hash into its database. Model Objects that
represent these data types can be "created" in cbapi by using the ``create()`` method::

    >>> bh = cb.create(BannedHash)

If you attempt to create a Model Object that cannot be created, you will receive a :py:mod:`ApiError` exception.

Once a Model Object is created, it's blank (it has no data). You will need to set the required properties and then call
the ``.save()`` method::

    >>> bh = cb.create(BannedHash)
    >>> bh.text = "Banned from API"
    >>> bh.md5sum = "CA4FAFFA957C71C006B59E29DFE3EB8B"
    >>> bh.save()

If you don't fill out all the properties required by the API, then you will receive an :py:mod:`InvalidObjectError`
exception with a list of the properties that are required and not currently set.

Once the ``.save()`` method is called, the appropriate REST API call is made to create the object. The Model Object
is then updated to the current state returned by the API, which may include additional data properties initialized
by EDR or App Control.

Modifying Existing Objects
--------------------------

The same ``.save()`` method can be used to modify existing Model Objects if the REST API provides that capability.
If you attempt to modify a Model Object that cannot be changed, you will receive a :py:mod:`ApiError` exception.

For example, if you want to change the "jgarman" user's password to "cbisawesome"::

    >>> user = cb.select(User, "jgarman")
    >>> user.password = "cbisawesome"
    >>> user.save()

Deleting Objects
----------------

Simply call the ``.delete()`` method on a Model Object to delete it (again, if you attempt to delete a Model Object
that cannot be deleted, you will receive a :py:mod:`ApiError` exception).

Example::

    >>> user = cb.select(User, "jgarman")
    >>> user.delete()

Tracking Changes to Objects
---------------------------

Internally, Model Objects track all changes between when they were last refreshed from the server up until ``.save()``
is called. If you're interested in what properties have been changed or added, simply ``print`` the Model Object.

You will see a display like the following::

    >>> user = cb.create(User)
    >>> user.username = "jgarman"
    >>> user.password = "cbisawesome"
    >>> user.first_name = "Jason"
    >>> user.last_name = "Garman"
    >>> user.teams = []
    >>> user.global_admin = False
    >>> print(user)
    User object, bound to https://cbserver.
     Partially initialized. Use .refresh() to load all attributes
    -------------------------------------------------------------------------------

    (+)                email: jgarman@carbonblack.com
    (+)           first_name: Jason
    (+)         global_admin: False
                          id: None
    (+)            last_name: Garman
    (+)             password: cbisawesome
    (+)                teams: []
    (+)             username: jgarman

Here, the ``(+)`` symbol before a property name means that the property will be added the next time that ``.save()``
is called. Let's call ``.save()`` and modify one of the Model Object's properties::

    >>> user.save()
    >>> user.first_name = "J"
    >>> print(user)
    print(user)
    User object, bound to https://cbserver.
     Last refreshed at Mon Nov  7 16:54:00 2016
    -------------------------------------------------------------------------------

                       email: jgarman@carbonblack.com
    (*)           first_name: J
                global_admin: False
                          id: jgarman
                   last_name: Garman
                       teams: []
                    username: jgarman

The ``(*)`` symbol means that a property value will be changed the next time that ``.save()`` is called. This time,
let's forget about our changes by calling ``.reset()`` instead::

    >>> user.reset()
    >>> print(user.first_name)
    Jason

Now the user Model Object has been restored to the original state as it was retrieved from the server.
