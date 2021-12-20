CB LiveQuery API Examples
=========================

Let's cover a few example functions that our LiveQuery Python bindings enable. To begin, we need to import the
relevant libraries::

    >>> import sys
    >>> from cbapi.psc.livequery import CbLiveQueryAPI
    >>> from cbapi.psc.livequery.models import Run, Result


Now that we've imported the necessary libraries, we can perform some queries on our endpoints.

Create a Query Run
----------------------------------

Let's create a Query Run. First, we specify which profile to use for authentication from our credentials.psc file and
create the LiveQuery object.

    >>> profile = "default'
    >>> cb = CbLiveQueryAPI(profile=profile)

Now, we specify the SQL query that we want to run, name of the run, device IDs, and device types.

    >>> sql = 'select * from logged_in_users;'
    >>> name_of_run = 'Selecting all logged in users'
    >>> device_ids = '1234567'
    >>> device_types = 'WINDOWS'

Now, we create a query and add these values to it.

    >>> query = cb.query(sql)
    >>> query.name(name_of_run)
    >>> query.device_ids(device_ids)
    >>> query.device_types(device_types)

Finally, we submit the query and print the results.

    >>> run = query.submit()
    >>> print(run)

This query should return all logged in Windows endpoints with a ``device_id`` of ``1234567``.

The same query can be executed with the example script
`manage_run.py <https://github.com/carbonblack/cbapi-python/blob/master/examples/livequery/manage_run.py>`_. ::

    python manage_run.py --profile default create --sql 'select * from logged_in_users;' --name 'Selecting all logged in users' --device_ids '1234567' --device_types 'WINDOWS'

Other possible arguments to ``manage_run.py`` include ``--notify`` and ``--policy_ids``.

Get Query Run Status
---------------------

Now that we've created a Query Run, let's check the status. If we haven't already authenticated with a credentials
profile, we begin by specifying which profile to authenticate with.

    >>> profile = 'default'
    >>> cb = CbLiveQueryAPI(profile=profile)

Next, we select the run with the unique run ID.

    >>> run_id = 'a4oh4fqtmrr8uxrdj6mm0mbjsyhdhhvz'
    >>> run = cb.select(Run, run_id)
    >>> print(run)

This can also be accomplished with the example script
`manage_run.py <https://github.com/carbonblack/cbapi-python/blob/master/examples/livequery/manage_run.py>`_::

    python manage_run.py --profile default --id a4oh4fqtmrr8uxrdj6mm0mbjsyhdhhvz

In addition, you can specify which order you want results returned. To change from the default ascending order, use
the flag ``-d`` or ``--descending_results``::

    python manage_run.py --profile default --id a4oh4fqtmrr8uxrdj6mm0mbjsyhdhhvz --descending_results

Get Query Run Results
---------------------

Let's view the results of a run. If we haven't already authenticated, we must start with that.

    >>> profile = 'default'
    >>> cb = CbLiveQueryAPI(profile=profile)

To view the results of a run, we must specify the run ID.

    >>> run_id = 'a4oh4fqtmrr8uxrdj6mm0mbjsyhdhhvz'
    >>> results = cb.select(Result).run_id(run_id)

Finally, we print the results.

    >>> for result in results:
    ...     print(result)

Results can be narrowed down with the following criteria::

    device_ids
    status

Examples of using these criteria are below::

    >>> device_id = '1234567'
    >>> results.criteria(device_id=device_id)
    >>> status = 'matched'
    >>> results.criteria(status=status)

Finally, we print the results.

    >>> for result in results:
    ...     print(result)


You can also retrieve run results with the example script
`run_search.py <https://github.com/carbonblack/cbapi-python/blob/master/examples/livequery/run_search.py>`_::

    python run_search.py --profile default --id a4oh4fqtmrr8uxrdj6mm0mbjsyhdhhvz --device_ids '1234567' --status 'matched'
