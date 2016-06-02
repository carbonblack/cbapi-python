# Nose Tests

## Test Caches

Already created caches are in the `caches` directory.  Note that the version of requests_cache is modified in such a way
that enables easier diffing.  So you must use our version to use diffing scripts.  Otherwise you can use the official version.
Also note that the existing test caches are in the modified format and will not work with the official request_cache.

## Required packages

* nose
* nose-testconfig
* nose-progressive

## Test config file

Example config file

    [cache]
    #
    # Use the golden cache.  Ignores all other parameters
    #
    use_golden = true

    #
    # true - deletes the cache specified by cachefilename and create a new cache database
    # false - uses the cache database file specified by 'cachefilename'
    #
    cache_overwrite = false

    #
    # Name of the cache
    # Note: .sqlite is added to the filename
    #
    cache_filename = nosetestcache

For this example case a file named nosetestcache.sqlite will be created if it does not already exist.  If the sqlite file exists, request_cache will use that file
for its caching. If use_golden is set to `true` then assertion tests will be run.


## Performing tests
 Example:

    nosetests -s -v --tc-file nosetest.cfg --with-progressive