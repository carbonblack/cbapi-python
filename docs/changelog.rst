CbAPI Changelog
===============
.. top-of-changelog (DO NOT REMOVE THIS COMMENT)

CbAPI 1.7.2 - Released July 22, 2020
------------------------------------

Updates

* General
    * Allow passing in proxy configuration as direct parameters during class instantiation of base API.


CbAPI 1.7.1 - Released July 22, 2020
------------------------------------

Updates

* General
    * Documentation updates to indicate changed product names
* Carbon Black Cloud
    * Process Search v2 rows defaults to 10k to match UI behavior
* CB Response
    * Add support for fetching alert by ID


CbAPI 1.7.0 - Released July 14, 2020
------------------------------------

Updates

* General
    * Updates to pool defaults in base API.
    * Changes to exception handling to better discriminate ConnectionErrors and queries with invalid syntax.
    * Various minor bug fixes throughout.
* Carbon Black Cloud
    * Bug fixes to query implementation.
    * Live Response: Account for sensor queue depth when submitting jobs.
* CB Defense
    * Added examples for Dell BIOS verification.
* CB ThreatHunter
    * Bug fixes to query implementation.
    * Update process and event searches to v2.
    * examples/create_feed: Make report optional during feed creation
    * examples/process_exporter: Add headers to CSV file writer
    * examples/threat_intelligence: Simplify report validation, add severity conversion to percent

CbAPI 1.6.2 - Released April 08, 2020
-------------------------------------

Updates

* CB Response
    * Changes to align with limits placed on the sensor update function in CB Response 7.1.0. Release notes are available on User Exchange, the ID is `CB 28683 <https://community.carbonblack.com/t5/Documentation-Downloads/CB-Response-7-1-0-Server-Release-Notes/ta-p/88027>`_.

CbAPI 1.6.1 - Released January 13, 2020
---------------------------------------

Updates

* CB Response
	* Fix Alert.save() to use alert v1 API
* Carbon Black Cloud
	* Fix Live Response flow to use integrationServices/v3/device to prevent need for multiple API keys
* CB ThreatHunter
	* Update example for ThreatHunter Query

CbAPI 1.6.0 - Released December 3, 2019
---------------------------------------

Updates

* New Carbon Black Cloud API Support
	* Support for Devices v6:
		* List and search for devices
		* Export device information to CSV
		* Device control actions: quarantine, bypass, background scan, deregister/delete, update
	* Support for Alerts v6:
		* Search for and retrieve alerts
		* Update alert status (dismiss alerts)

Examples

* Devices v6:
	*	psc/device_control.py
	*	psc/download_device_list.py
	*	psc/list_devices.py
* Alerts v6:
	*	psc/alert_search_suggestions.py
	*	psc/bulk_update_alerts.py
	*	psc/bulk_update_cbanalytics_alerts.py
	*	psc/bulk_update_threat_alerts.py
	*	psc/bulk_update_vmware_alerts.py
	*	psc/bulk_update_watchlist_alerts.py
	*	psc/list_alert_facets.py
	*	psc/list_alerts.py
	*	psc/list_cbanalytics_alert_facets.py
	*	psc/list_cbanalytics_alerts.py
	*	psc/list_vmware_alert_facets.py
	*	psc/list_vmware_alerts.py
	*	psc/list_watchlist_alert_facets.py
	*	psc/list_watchlist_alerts.py

CbAPI 1.5.6 - Released November 19, 2019
----------------------------------------

Updates

* General
    * Name change to Carbon Black Cloud from PSC.

CbAPI 1.5.5 - Released November 12, 2019
----------------------------------------

Updates

* CB ThreatHunter
    * Fix List object that was not callable.

CbAPI 1.5.4 - Released October 24, 2019
----------------------------------------

Updates

* General
    * Prevent pytest from blocking python2 install

* CB Response
    * Fix python2 function overwrite for max_children

CbAPI 1.5.3 - Released October 15, 2019
----------------------------------------

Updates

* General
    * Fix MoreThanOneResultError
    * Add environmental org key

* CB ThreatHunter
    * Fix iterating process search results
    * Fix watchlist reports fetch
    * Fix process.summary


CbAPI 1.5.2 - Released September 9, 2019
----------------------------------------

Updates

* CB Response
    * Add support for max_children on Process search
* CB LiveOps
    * Add LQ device summaries
    * Add faceting for LQ results and LQ device summaries
    * Add LQ run history
* CB ThreatHunter
    * Fix an invalid search job creation

CbAPI 1.5.1 - Released July 23, 2019
----------------------------------------

Updates

* CB Response
    * Require CBAPI users to obtain their API token from the CB Response console.
* CB LiveOps
    * Fixing a build issue


CbAPI 1.5.0 - Released July 23, 2019
----------------------------------------

Updates

* CB LiveOps
    * Start new LiveQuery (LQ) runs
    * Fetch LQ results
    * View LQ run status
    * Filter on LQ results
* PSC Org Key Management
    * Added support for org key management within CBAPI
    * Credentials utility for org keys
    * PR #166, #169, #170

Examples

* LiveQuery - manage_run.py
* LiveQuery - run_search.py


CbAPI 1.4.5 - Released July 11, 2019
----------------------------------------

Updates

* CB ThreatHunter
    * Route updates for process search, feed management, watchlist management
    * Enforce org_key presence
    * Org-based process search
    * Org-based event search
    * Org-based tree queries
* Minor updates for Python3 Compatibility

Examples

* Updated CB TH Process Search Example
* Added process_guid to process_tree example for ThreatHunter

CbAPI 1.4.4 - Released July 3, 2019
----------------------------------------

Updates

* Carbon Black UBS Support PR `#142 <https://github.com/carbonblack/cbapi-python/pull/142>`_
* CB Response - Fixing bulk update for Alerts to use v1 route
* Updates to use yaml safe_load `#157 <https://github.com/carbonblack/cbapi-python/pull/157>`_

Examples

* Refactored Carbon Black ThreatHunter examples
* Added process_guid to process_tree example for ThreatHunter

CbAPI 1.4.3 - Released May 7, 2019
----------------------------------------

Updates

* CB ThreatHunter - Feed fixes `#156 <https://github.com/carbonblack/cbapi-python/pull/156>`_
* CB Response - Change Alert model object to use v2 route `#155 <https://github.com/carbonblack/cbapi-python/pull/155>`_
* CB Response - Only view active LR sessions `#154 <https://github.com/carbonblack/cbapi-python/pull/154>`_
* Removing refs to VT alliance feeds `#144 <https://github.com/carbonblack/cbapi-python/pull/144>`_

Examples

* CB Defense - Create list_events_with_cmdline_csv.py `#152 <https://github.com/carbonblack/cbapi-python/pull/152>`_
* CB Defense - Updated import link to proper module `#148 <https://github.com/carbonblack/cbapi-python/pull/148>`_

CbAPI 1.4.2 - Released March 27, 2019
----------------------------------------

This release introduces additional support for CB PSC's ThreatHunter APIs

* Threat Intelligence APIs

CbAPI 1.4.1 - Released January 10, 2019
----------------------------------------

* Bug fixes
* Adding to authorized error to make it clear that users should check API creds

CbAPI 1.4.0 - Released January 10, 2019
----------------------------------------

This release introduces support for CB PSC's ThreatHunter APIs

* Process, Tree, and Search are supported with more to come

CbAPI 1.3.6 - Released February 14, 2018
----------------------------------------

This release has one critical fix:

* Fix a fatal exception when connecting to CB Response 6.1.x servers

CbAPI 1.3.5 - Released February 2, 2018
---------------------------------------

This release includes bugfixes and contributions from the Carbon Black community.

All products:

* More Python 3 compatibility fixes.
* Fix the ``wait_for_completion`` and ``wait_for_output`` options in the Live Response ``.create_process()`` method.
  If ``wait_for_completion`` is True, the call to ``.create_process()`` will block until the remote process
  has exited. If ``wait_for_output`` is True, then ``.create_process()`` will additionally wait until the output
  of the remote process is ready and return that output to the caller. Setting ``wait_for_output`` to True automatically
  sets ``wait_for_completion`` to True as well.
* The ``BaseAPI`` constructor now takes three new optional keyword arguments to control the underlying connection
  pool: ``pool_connections``, ``pool_maxsize``, and ``pool_block``. These arguments are sent to the underlying
  ``HTTPAdapter`` used when connecting to the Carbon Black server. For more information on these parameters, see
  the `Python requests module API documentation for HTTPAdapter <http://docs.python-requests.org/en/master/api/#requests.adapters.HTTPAdapter>`_.

CB Defense:

* Date/time stamps in the Device model object are now represented as proper Python datetime objects, rather than
  integers.
* The ``policy_operations.py`` example script's "Replace Rule" command is fixed.
* Add the CB Live Response job-based API.
* Add a new example script ``list_devices.py``

CB Response:

* The ``Process`` and ``Binary`` model objects now return None by default when a non-existent attribute is referenced,
  rather than throwing an exception.
* Fixes to ``walk_children.py`` example script.
* Fix exceptions in enumerating child processes, retrieving path and MD5sums from processes.
* Multiple ``.where()`` clauses can now be used in the ``Sensor`` model object.
* Workaround implemented for retrieving/managing more than 500 banned hashes.
* Alert bulk operations now work on batches of 500 alerts.
* ``.flush_events()`` method on ``Sensor`` model object no longer throws an exception on CB Response 6.x servers.
* ``.restart_sensor()`` method now available for ``Sensor`` model object.
* Fix ``user_operations.py`` example script to eliminate exception when adding a new user to an existing team.
* Add ``.remove_team()`` method on ``User`` model object.
* Automatically set ``cb.legacy_5x_mode`` query parameter for all Process queries whenever a legacy Solr core (from
  CB Response 5.x) is loaded.
* Added ``.use_comprehensive_search()`` method to enable the "comprehensive search" option on a Process query.
  See the `CB Developer Network documentation on Comprehensive Search
  <https://developer.carbonblack.com/reference/enterprise-response/6.1/process-api-changes/#process-joining-comprehensive-search>`_
  for more information on "comprehensive search".
* Add ``.all_childprocs()``, ``.all_modloads()``, ``.all_filemods()``, ``.all_regmods()``, ``.all_crossprocs()``,
  and ``.all_netconns()`` methods to retrieve process events from all segments, rather than the current process segment.
  You can also use the special segment "0" to retrieve process events across all segments.
* Fix ``cmdline_filters`` in the ``IngressFilter`` model object.

CB Protection:

* Tamper Protection can now be set and cleared in the ``Computer`` model object.


CbAPI 1.3.4 - Released September 14, 2017
-----------------------------------------

This release includes a critical security fix and small bugfixes.

Security fix:

* The underlying CbAPI connection class erroneously disabled hostname validation by default. This does *not* affect
  code that uses CbAPI through the public interfaces documented here; it only affects code that accesses the new
  ``CbAPISessionAdapter`` class directly. This class was introduced in version 1.3.3.
  Regardless, it is strongly recommended that all users currently using 1.3.3 upgrade to 1.3.4.

Bug fixes:

* Add rule filename parameter to CB Defense ``policy_operations.py`` script's ``add-rule`` command.
* Add support for ``tamperProtectionActive`` attribute to CB Protection's ``Computer`` object.
* Work around CB Response issue- the ``/api/v1/sensor`` route incorrectly returns an HTTP 500 if no sensors match the
  provided query. CbAPI now catches this exception and will instead return an empty set back to the caller.


CbAPI 1.3.3 - Released September 1, 2017
----------------------------------------

This release includes security improvements and bugfixes.

Security changes:

* CbAPI enforces the use of HTTPS when connecting to on-premise CB Response servers.
* CbAPI can optionally require TLSv1.2 when connecting to Carbon Black servers.

  * Note that some versions of Python and OpenSSL, notably the version of OpenSSL packaged with Mac OS X, do not support
    TLSv1.2. This will cause CbAPI to fail to connect to CB Response 6.1+ servers which require TLSv1.2 cipher suites.
  * A new command, ``cbapi check-tls``, will report the TLS version supported by your platform.
  * To enforce the use of TLSv1.2 when connecting to a server, add ``ssl_force_tls_1_2=True`` to that server's
    credential profile.

* Add the ability to "pin" a specific server certificate to a credential profile.

  * You can now force TLS certificate verification on self-signed, on-premise installations of CB Response or Protection
    through the ``ssl_cert_file`` option in the credential profile.
  * To "pin" a server certificate, save the PEM-formatted server certificate to a file, and put the full path to that
    PEM file in the ``ssl_cert_file`` option of that server's credential profile.
  * When using this option with on-premise CB Response servers, you may also have to set
    ``ssl_verify_hostname=False`` as the hostname in the certificate generated at install time is ``localhost`` and
    will not match the server's hostname or IP address. This option will still validate that the server's certificate
    is valid and matches the copy in the ``ssl_cert_file`` option.

Changes for CB Protection:

* The API now sets the appropriate "GET" query fields when changing fields such as the ``debugFlags`` on the Computer
  object.
* The ``.template`` attribute on the Computer model object has been renamed ``.templateComputer``.
* Remove AppCatalog and AppTemplate model objects.

Changes for CB Response:

* Added ``.webui_link`` property to CB Response Query objects.
* Added ``ban_hash.py`` example.

Bug Fixes:

* Error handling is improved on Python 3. Live Response auto-reconnect functionality is now fixed on Python 3 as
  a result.
* Workaround implemented for CB Response 6.1 where segment_ids are truncated on Alerts. The ``.process`` attribute on
  an Alert now ignores the ``segment_id`` and links to the first Process segment.
* Fixed issue with ``Binary.signed`` and ``CbModLoadEvent.is_signed``.


CbAPI 1.3.2 - Released August 10, 2017
--------------------------------------

This release introduces the Policy API for CB Defense. A sample ``policy_operations.py`` script is now included
in the ``examples`` directory for CB Defense.

Other changes:

* CB Response

  * Bugfixes to the ``User`` Model Object.
  * New ``user_operations.py`` example script to manage users & teams.
  * Additional ``Team`` Model Object to add/remove/modify user teams.
  * New ``check_datasharing.py`` example script to check if third party data sharing is enabled for binaries on any sensor groups.
  * Documentation fix for the ``User`` Model Object.
  * Fix to the ``watchlist_operations.py`` example script.


CbAPI 1.3.1 - Released August 3, 2017
-------------------------------------

This is a bugfix release with minor changes:

* CB Response

  * Add ``partition_operations.py`` script to demonstrate the use of the StoragePartition model object.
  * Fix errors when accessing the ``.start`` attribute of child processes.
  * Fix errors generated by the ``walk_children.py`` example script. The output has been changed as well to indicate
    the process lifetime, console UI link, and command lines.
  * Add an ``.end`` attribute to the Process model object. This attribute reports back either ``None`` if the
    process is still executing, or the last event time associated with the process if it has exited. See the
    ``walk_children.py`` script for an example of how to calculate process lifetime.
  * Fix errors when using the ``.parents`` attribute of a Process.
  * Add ``wait_for_completion`` flag to ``create_process`` Live Response method, and default to ``True``. The
    ``create_process`` method will now wait for the target process to complete before returning.

* CB Defense

  * Add ``wait_for_completion`` flag to ``create_process`` Live Response method, and default to ``True``. The
    ``create_process`` method will now wait for the target process to complete before returning.


CbAPI 1.3.0 - Released July 27, 2017
------------------------------------

This release introduces the Live Response API for CB Defense. A sample ``cblr_cli.py`` script is now included in the
``examples`` directory for both CB Response and CB Defense.

Other changes:

* CB Protection

  * You can now create new ``FileRule`` and ``Policy`` model objects in cbapi.

* CB Response

  * Added ``watchlist_exporter.py`` and ``watchlist_importer.py`` scripts to the CB Response examples directory.
    These scripts allow you to export Watchlist data in a human- and machine-readable JSON format and then re-import them into another CB Response server.
  * The ``Sensor`` Model Object now uses the non-paginated (v1) API by default. This fixes any issues encountered when
    iterating over all the sensors and receiving duplicate and/or missing sensors.
  * Fix off-by-one error in ``CbCrossProcess`` object.
  * Fix issue iterating through ``Process`` Model Objects when accessing processes generated from a 5.2 server
    after upgrading to 6.1.
  * Reduce number of API requests required when accessing sibling information (parents, children, and siblings) from the
    ``Process`` Model Object.
  * Retrieve all events for a process when using ``segment`` ID of zero on a CB Response 6.1 server.
  * Behavior of ``Process.children`` attribute has changed:

    * Only one entry is present per child (before there were up to two; one for the spawn event, one for the
      terminate event)
    * The timestamp is derived from the start time of the process, not the timestamp from the spawn event.
      the two timestamps will be off by a few microseconds.
    * The old behavior is still available by using the ``Process.childprocs`` attribute instead. This incurs a
      performance penalty as another API call will have to be made to collect the childproc information.

  * ``Binary`` Model Object now returns False for ``.is_signed`` attribute if it is set to ``(Unknown)``.

* Moved the ``six`` Python module into cbapi and removed the external dependency.

CbAPI 1.2.0 - Released June 22, 2017
------------------------------------

This release introduces compatibility with our new product, CB Defense, as well as adding new Model Objects introduced
in the CB Protection 8.0 APIs.

Other changes:

* CB Response

  * New method ``synchronize()`` added to the ``Feed`` Model Object

* Bug fixes and documentation improvements

CbAPI 1.1.1 - Released June 2, 2017
-----------------------------------

This release includes compatibility fixes for CB Response 6.1. Changes from 1.0.1 include:

* Substantial changes to the ``Process`` Model Object for CB Response 6.1. See details below.
* New ``StoragePartition`` Model Object to control Solr core loading/unloading in CB Response 6.1.
* New ``IngressFilter`` Model Object to control ingress filter settings in CB Response 6.1.
* Fix issues with ``event_export.py`` example script.
* Add ``.all_events`` property to the ``Process`` Model Object to expose a list of all events across all segments.
* Add example script to perform auto-banning based on watchlist hits from CB Event Forwarder S3 output files.
* Add bulk operations to the ``ThreatReport`` and ``Alert`` Query objects:

  * You can now call ``.set_ignored()``, ``.assign()``, and ``.change_status()`` on an ``Alert`` Query object to change
    the respective fields for every Alert that matches the query.
  * You can now call ``.set_ignored()`` on a ``ThreatReport`` Query object to set or clear the ignored flag for every
    ThreatReport that matches the query.

Changes to ``Process`` Model Object for CB Response 6.1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CB Response 6.1 uses a new way of recording process events that greatly increases the speed and scale of collection,
allowing you to store and search data for more endpoints on the same hardware. Details on the new database format
can be found on the Developer Network website at the `Process API Changes for CB Response 6.0
<https://developer.carbonblack.com/reference/enterprise-response/6.1/process-api-changes/>`_ page.

The ``Process`` Model Object traditionally referred to a single "segment" of events in the CB Response database. In
CB Response versions prior to 6.0, a single segment will include up to 10,000 individual endpoint events, enough to
handle over 95% of the typical event activity for a given process. Therefore, even though a ``Process`` Model Object
technically refers to a single *segment* in a process, since most processes had less than 10,000 events and therefore
were only comprised of a single segment, this distinction wasn't necessary.

However, now that processes are split across many segments, a better way of handling this is necessary. Therefore,
CB Response 6.0 introduces the new ``.group_by()`` method. This method is new in cbapi 1.1.0 and is part of five
new query filters available when communicating with a CB Response 6.1 server. These filters are accessible via methods
on the ``Process`` Query object. These new methods are:

* ``.group_by()`` - Group the result set by a field in the response. Typically you will want to group by ``id``, which
  will ensure that the result set only has one result per *process* rather than one result per *event segment*. For
  more information on processes, process segments, and how segments are stored in CB Response 6.0, see the
  `Process API Changes for CB Response 6.0 <https://developer.carbonblack.com/reference/enterprise-response/6.1/process-api-changes/>`_
  page on the Developer Network website.
* ``.min_last_update()`` - Only return processes that have events after a given date/time stamp (relative to the
  individual sensor's clock)
* ``.max_last_update()`` - Only return processes that have events before a given date/time stamp (relative to the
  individual sensor's clock)
* ``.min_last_server_update()`` - Only return processes that have events after a given date/time stamp (relative to the
  CB Response server's clock)
* ``.max_last_server_update()`` - Only return processes that have events before a given date/time stamp (relative to the
  CB Response server's clock)

Examples for new Filters
~~~~~~~~~~~~~~~~~~~~~~~~

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

Notice that the "same" process ID is returned seven times, but with seven different segment IDs. CB Response will
return *every* process event segment that matches a given query, in this case, any event segment that contains the
process command name ``cmd.exe``.

That is, however, most likely not what you wanted. Instead, you'd like a list of the *unique* processes associated with
the command name ``cmd.exe``. Just add the ``.group_by("id")`` filter to your query::

    >>> for proc in c.select(Process).where("process_name:cmd.exe").min_last_update(yesterday).group_by("id"):
    ...     print proc.id, proc.segment
    DEBUG:cbapi.connection:HTTP GET /api/v1/process?cb.group=id&cb.min_last_update=2017-05-21T18%3A41%3A58Z&cb.urlver=1&facet=false&q=process_name%3Acmd.exe&rows=100&sort=last_update+desc&start=0 took 2.163s (response 200)
    00000001-0000-0e48-01d2-c2a397f4cfe0 1495465643405
