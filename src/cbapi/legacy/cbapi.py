#
# CARBON BLACK API
# Copyright Bit9, Inc. 2014
# support@carbonblack.com
#

# NOTE: This API is deprecated. See the cbapi.response.rest_api documentation.
from warnings import warn

import json
import time
import requests
import urllib
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except:
    pass


# Provide the ability to validate a Carbon Black server's SSL certificate without validating the hostname
# (by default Carbon Black certificates are "issued" as CN=Self-signed Carbon Black Enterprise Server HTTPS Certificate)
class HostNameIgnoringAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       assert_hostname=False, **pool_kwargs)


class CbApi(object):
    """ Python bindings for Carbon Black API
    Example:

    import cbapi
    cb = cbapi.CbApi("http://cb.example.com", token="apitoken")
    # get metadata for all svchost.exe's not from c:\\windows
    procs = cb.process_search(r"process_name:svchost.exe -path:c:\\windows\\")
    for proc in procs['results']:
        proc_detail = cb.process(proc['id'])
        print proc_detail['process']['start'], proc_detail['process']['hostname'], proc_detail['process']['path']
    """
    def __init__(self, server, ssl_verify=True, token=None, ignore_system_proxy=False,
                 use_https_proxy=None, ssl_verify_hostname=True, use_http_proxy=None):
        """ Requires:
                server -    URL to the Carbon Black server.  Usually the same as
                            the web GUI.
                ssl_verify - verify server SSL certificate
                token - this is for CLI API interface
        """

        # We will uncomment this once cbapi 1.0.0 is released
        # warn("CbApi is deprecated and will be removed as of cbapi 2.0.0.", DeprecationWarning)

        if not server.startswith("http"):
            raise TypeError("Server must be URL: e.g, http://cb.example.com")

        if token is None:
            raise TypeError("Missing required authentication token.")

        self.server = server.rstrip("/")
        self.ssl_verify = ssl_verify
        self.token = token
        self.token_header = {'X-Auth-Token': self.token}
        self.session = requests.Session()

        if not ssl_verify_hostname:
            self.session.mount("https://", HostNameIgnoringAdapter())

        self.proxies = {}
        if ignore_system_proxy:         # see https://github.com/kennethreitz/requests/issues/879
            self.proxies = {
                'no': 'pass'
            }
        else:
            if use_http_proxy:
                self.proxies['http'] = use_http_proxy
            if use_https_proxy:
                self.proxies['https'] = use_https_proxy

    def decode_json_response(self, r, default=None):
        if r.status_code == 204:
            return default
        else:
            return json.loads(r.content)

    def info(self):
        """ Provide high-level information about the Carbon Black Enterprise Server.

            **NOTE** This function is provided for convenience and may change in
                     future versions of the Carbon Black API

            Returns a python dictionary with the following field:
                - version - version of the Carbon Black Enterprise Server
        """
        r = self.cbapi_get("%s/api/info" % self.server)
        r.raise_for_status()
        return json.loads(r.content)

    def license_status(self):
        """ Provide a summary of the current applied license
        """
        r = self.cbapi_get("%s/api/v1/license" % (self.server,))
        r.raise_for_status()
        return json.loads(r.content)

    def apply_license(self, license):
        """ Apply a new license to the server
        """
        r = self.cbapi_post("%s/api/v1/license" % (self.server,),
                            data=json.dumps({'license': license}))
        r.raise_for_status()

    def get_platform_server_config(self):
        """ Get Bit9 Platform Server configuration
            This includes server address and authentication information

            Must authenticate as a global administrator for this data to be available

            Note: the secret is never available (via query) for remote callers, although
                  it can be applied
        """
        r = self.cbapi_get("%s/api/v1/settings/global/platformserver" % (self.server,))
        r.raise_for_status()
        return json.loads(r.content)

    def set_platform_server_config(self, platform_server_config):
        """ Sets the Bit9 Platform Server configuration
            This includes the server address, username, and password

            Must authenticate as a global administrator to have the rights to set this config

            platform_server_config is expected to be a python dictionary with the following keys:
                username : username for authentication
                password : password for authentication
                server   : server address
        """
        r = self.cbapi_post("%s/api/v1/settings/global/platformserver" % (self.server,),
                            data=json.dumps(platform_server_config))
        r.raise_for_status()

    def get_dashboard_stats(self):
        url = "%s/api/v1/dashboard/statistics" % (self.server)
        r = self.cbapi_get(url, timeout=120)
        r.raise_for_status()
        return r.json()

    def process_search(self, query_string, start=0, rows=10, sort="last_update desc", facet_enable=True):
        """ Search for processes.  Arguments:

            query_string -      The Cb query string; this is the same string used in the
                                "main search box" on the process search page.  "Contains text..."
                                See Cb Query Syntax for a description of options.

            start -             Defaulted to 0.  Will retrieve records starting at this offset.
            rows -              Defaulted to 10. Will retrieve this many rows.
            sort -              Default to last_update desc.  Must include a field and a sort
                                order; results will be sorted by this param.
            facet_enable -      Enable facets on the result set. Defaults to enable facets (True)

            Returns a python dictionary with the following primary fields:
                - results - a list of dictionaries describing each matching process
                - total_results - the total number of matches
                - elapsed - how long this search took
                - terms - a list of strings describing how the query was parsed
                - facets - a dictionary of the facet results for this search
        """

        # setup the object to be used as the JSON object sent as a payload
        # to the endpoint

        if facet_enable:
            facet_param = ['true', 'true']
        else:
            facet_param = ['false', 'false']

        params = {
            'sort': sort,
            'facet': facet_param,
            'rows': rows,
            'cb.urlver': ['1'],
            'start': start}

        # a q (query) param only needs to be specified if a query is present
        # to search for all processes, provide an empty string for q
        #
        if len(query_string) > 0:
            params['q'] = [query_string]

        # HTTP POST and HTTP GET are both supported for process search
        # HTTP POST allows for longer query strings
        #
        r = self.cbapi_post("%s/api/v1/process" % self.server, data=json.dumps(params))
        r.raise_for_status()
        return r.json()

    def process_summary(self, id, segment, children_count=15):
        """ get the detailed metadata for a process.  Requires the 'id' field from a process
            search result, as well as a segment, also found from a process search result.
            The results will be limited to children_count children metadata structures.

            Returns a python dictionary with the following primary fields:
                - process - metadata for this process
                - parent -  metadata for the parent process
                - children - a list of metadata structures for child processes
                - siblings - a list of metadata structures for sibling processes
        """
        r = self.cbapi_get("%s/api/v1/process/%s/%s?children=%d" % (self.server, id, segment, children_count))
        r.raise_for_status()
        return r.json()

    def process_events(self, id, segment):
        """ get all the events (filemods, regmods, etc) for a process.  Requires the 'id' and 'segment_id' fields
            from a process search result"""
        r = self.cbapi_get("%s/api/v1/process/%s/%s/event" % (self.server, id, segment))
        r.raise_for_status()
        return r.json()

    def process_report(self, id, segment=0):
        """ download a "report" package describing the process
            the format of this report is subject to change"""
        r = self.cbapi_get("%s/api/v1/process/%s/%s/report" % (self.server, id, segment))
        r.raise_for_status()
        return r.content

    def binary_search(self, query_string, start=0, rows=10, sort="server_added_timestamp desc", facet_enable=True):
        """ Search for binaries.  Arguments:


            query_string -      The Cb query string; this is the same string used in the
                                "main search box" on the binary search page.  "Contains text..."
                                See Cb Query Syntax for a description of options.

            start -             Defaulted to 0.  Will retrieve records starting at this offset.

            rows -              Defaulted to 10. Will retrieve this many rows.
            sort -              Default to server_added_timestamp desc.  Must include a field and a sort
                                order; results will be sorted by this param.
            facet_enable -      Enable facets on the result set. Defaults to enable facets (True)

            Returns a python dictionary with the following primary fields:
                - results - a list of dictionaries describing each matching binary
                - total_results - the total number of matches
                - elapsed - how long this search took
                - terms - a list of strings describing how the query was parsed
                - facets - a dictionary of the facet results for this saerch
        """
        if facet_enable:
            facet_param = ['true', 'true']
        else:
            facet_param = ['false', 'false']

        # setup the object to be used as the JSON object sent as a payload
        # to the endpoint
        params = {
            'sort': sort,
            'facet': facet_param,
            'rows': rows,
            'cb.urlver': ['1'],
            'start': start}

        # a q (query) param only needs to be specified if a query is present
        # to search for all binaries, provide an empty string for q
        if len(query_string) > 0:
            params['q'] = [query_string]

        # do a post request since the URL can get long
        # @note GET is also supported through the use of a query string
        r = self.cbapi_post("%s/api/v1/binary" % self.server, data=json.dumps(params))
        r.raise_for_status()
        return r.json()

    def binary_summary(self, md5):
        """ get the metadata for a binary.  Requires the md5 of the binary.

            Returns a python dictionary with the binary metadata. """
        r = self.cbapi_get("%s/api/v1/binary/%s/summary" % (self.server, md5))
        r.raise_for_status()
        return r.json()

    def binary(self, md5hash):
        """
        download binary based on md5hash
        """

        r = self.cbapi_get("%s/api/v1/binary/%s" % (self.server, md5hash))

        r.raise_for_status()
        return r._content

    def sensor(self, sensor_id):
        """
        get information about a single sensor, as specified by sensor id
        """

        r = self.cbapi_get("%s/api/v1/sensor/%s" % (self.server, sensor_id))
        r.raise_for_status()
        return r.json()

    def sensor_resourcestatus(self, sensor_id):
        """
        get resource utilization for a single sensor, as specified by sensor id
        """
        r = self.cbapi_get("%s/api/v1/sensor/%s/resourcestatus" % (self.server, sensor_id))
        r.raise_for_status()
        return self.decode_json_response(r, [])

    def sensors(self, query_parameters={}):
        """
        get sensors, optionally specifying search criteria

        as of this writing, supported search criteria are:
          ip - any portion of an ip address
          hostname - any portion of a hostname, case sensitive
          groupid - the sensor group id; must be numeric

        returns a list of 0 or more matching sensors
        """

        url = "%s/api/v1/sensor?" % (self.server,)
        for query_parameter in query_parameters.keys():
            url += "%s=%s&" % (query_parameter, query_parameters[query_parameter])

        r = self.cbapi_get(url)
        r.raise_for_status()
        return r.json()

    def sensor_installer(self, type, group_id=1):
        """
        get sensor installer package for a specified sensor group

        group_id - the group_id to download an installer for; defaults to 1 "Default Group"
        type - the sensor installer type.  [WindowsEXE|WindowsMSI|OSX|Linux]
        """

        # set up a mapping of types to REST endpoints
        #
        mapping = {\
                    'WindowsEXE': '/api/v1/group/%s/installer/windows/exe' % (group_id,),\
                    'WindowsMSI': '/api/v1/group/%s/installer/windows/msi' % (group_id,),\
                    'OSX':        '/api/v1/group/%s/installer/osx' % (group_id,),\
                    'Linux':      '/api/v1/group/%s/installer/linux' % (group_id,),\
                  }

        # verify that the type parameter is a known value
        #
        if not mapping.has_key(type):
            raise ValueError("Unrecognized type '%s'; should be one of 'WindowsEXE', 'WindowsMSI', 'OSX', or 'Linux'" % (type,))

        # build the fully-qualified URL
        #
        url = "%s%s" % (self.server, mapping[type])

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.content

    def sensor_backlog(self):
        """
        retrieves a summary of aggregate sensor backlog across all active sensors
        """

        url = "%s/api/v1/sensor/statistics" % (self.server,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def watchlist(self, id=None):
        """
        get all watchlists or a single watchlist
        """

        url = "%s/api/v1/watchlist" % (self.server)
        if id is not None:
            url = url + "/%s" % (id,)

        r = self.cbapi_get(url)
        r.raise_for_status()
        return r.json()

    def watchlist_add(self, type, name, search_query, id=None, readonly=False, basic_query_validation=True):
        """
        adds a new watchlist
        """

        # as directed by the caller, provide basic parameter validation
        if basic_query_validation:

            # ensure that the index type is either events or modules
            if "events" != type and "modules" != type:
                raise ValueError("type must be one of events or modules")

            # To maintain backwards compatibility, we must not urlencode queries that were submitted using the
            # "old" interface. The "old" interface was determined by searching for "q=" anywhere in the search_query
            # so we will retain that here. We are changing that condition slightly here and instead assuming that
            # either "q=" or "cb.urlver=" is the first parameter in a "preformatted" search_query.

            # Therefore there are two ways that someone could format search_query:
            # 1. Copy the query from an existing watchlist/URL exactly, which should be passed in to the API
            #    unchanged. This is equivalent to the "old" interface and will be referred to as a "preformatted"
            #    search_query. "preformatted" queries do not require url encoding.
            # 2. Copy the query from the query text box of the Web UI/API. In this case, the query must be url encoded
            #    then placed into a query string under the "q" key. Additionally, the cb.urlver key should be set
            #    to "1".

            encode_query = True

            # be backwards compatible with people still submitting
            # queries with q= at the beginning and just add cb.urlver=1&
            # This handles the "preformatted" case.
            if search_query.startswith("q=") and "cb.urlver" not in search_query:
                search_query = "cb.urlver=1&" + search_query
                encode_query = False
            # ensure that it starts with the proper url parameters
            elif search_query.startswith("cb.urlver=1&q="):
                encode_query = False

            # urlencode the query if necessary
            if encode_query:
                search_query = urllib.urlencode({
                    "q":         search_query,
                })
                # change all "+" to "%20" (percent-encoding)
                search_query = search_query.replace("+", "%20")
                # ensure that "cb.urlver=1" is the first parameter
                search_query = "cb.urlver=1&{}".format(search_query)

            # ensure that the query itself is properly encoded
            # This is now strengthened to enforce url encoding on all parameters
            for kvpair in search_query.split('&'):
                if len(kvpair.split('=')) != 2:
                    continue

                # the query itself must be percent-encoded
                # verify there are only non-reserved characters present
                # no logic to detect unescaped '%' characters
                for c in kvpair.split('=')[1]:
                    if c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~%":
                        raise ValueError("Unescaped non-reserved character '%s' found in query; use percent-encoding"
                                         % c)

        request = {
                      'index_type': type,
                      'name': name,
                      'search_query': search_query,
                      'readonly': readonly
                  }

        if id is not None:
            request['id'] = id

        url = "%s/api/v1/watchlist" % (self.server,)

        r = self.cbapi_post(url, data=json.dumps(request))
        r.raise_for_status()

        return r.json()

    def watchlist_del(self, id):
        """
        deletes a watchlist
        """
        request = {'id': id}

        url = "%s/api/v1/watchlist/%s" % (self.server, id)

        r = self.cbapi_delete(url, data=json.dumps(request))
        r.raise_for_status()

        return r.json()

    def watchlist_modify(self, id, watchlist):
        """
        updates a watchlist
        """
        url = "%s/api/v1/watchlist/%s" % (self.server, id)
        watchlist['search_query'] = urllib.quote(watchlist['search_query'])
        # ensure that it starts with the proper url parameters
        if not watchlist['search_query'].startswith("cb.urlver=1&q="):
            watchlist['search_query'] = "cb.urlver=1&q=" + watchlist['search_query']
        r = self.cbapi_put(url, data=json.dumps(watchlist))
        r.raise_for_status()

        return r.json()

    def feed_add_from_url(self, feed_url, enabled=True, validate_server_cert=False, use_proxy=False,
                          feed_username=None, feed_password=None, ssl_client_crt=None, ssl_client_key=None):
        """
        add a new feed to the Carbon Black server, as specified by URL
        """
        request = {
                      'use_proxy': use_proxy,
                      'validate_server_cert': validate_server_cert,
                      'feed_url': feed_url,
                      'enabled': enabled,
                  }

        if feed_username:
            request['username'] = feed_username
        if feed_password:
            request['password'] = feed_password

        if ssl_client_crt:
            request['ssl_client_crt'] = ssl_client_crt
        if ssl_client_key:
            request['ssl_client_key'] = ssl_client_key

        url = "%s/api/v1/feed" % (self.server,)

        r = self.cbapi_post(url, data=json.dumps(request))
        r.raise_for_status()

        return r.json()

    def user_add_from_data(self, username, first_name, last_name, password, confirm_password, global_admin, teams, email):
        """
        add a new user to the server
        """
        request = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'password': password,
            'confirm_password': confirm_password,
            'global_admin': global_admin,
            'teams': teams,
            'email': email,
        }
        url = "%s/api/user" % (self.server,)

        r = self.cbapi_post(url, data = json.dumps(request))
        r.raise_for_status()

        return r.json()

    def feed_get_id_by_name(self, name):
        """
        helper function to find the feed id given the feed name
        """

        for feed in self.feed_enum():
            if feed['name'].lower() == name.lower():
                return feed['id']

        # did not find it
        #
        return None

    def user_get_username_by_name(self, first_name, last_name):
        """
        helper function to find the username given a user's first and last name
        """

        for user in self.user_enum():
            if user['first_name'].lower() == first_name.lower() and user['last_name'].lower() == last_name.lower():
                return user['username']

        # did not find it
        #
        return None

    def feed_enum(self):
        """
        enumerate all configured feeds
        """

        url = "%s/api/v1/feed" % (self.server,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def user_enum(self):
        """
        enumerate all users
        """

        url = "%s/api/users" % (self.server,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def team_enum(self):
        """
        enumerate all teams
        """

        url = "%s/api/teams" % (self.server,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def group_enum(self):
        return

    def feed_info(self, id):
        """
        retrieve information about an existing feed, as specified by id

        note: the endpoint /api/v1/feed/<id> is not supported as of CB server 5.0
        """
        feeds = self.feed_enum()
        for feed in feeds:
          if str(feed['id']) == str(id):
              return feed

    def user_info(self, username):
        """
        retrieve information about an existing user, as specified by username

        note: the endpoint /api/users/<id> is not supported as of CB server 5.0
        """
        users = self.user_enum()
        for user in users:
          if user['username'] == username:
              return user

    def team_get_id_by_name(self, name):
        """
        retrieve information about an existing team, specified by name
        """

        teams = self.team_enum()
        for team in teams:
            if team['name'] == name:
                return team['id']

    def team_info(self, id):
        """
        retrieve information about an existing team, specified by id
        """

        teams = self.team_enum()
        for team in teams:
            print type(id)
            print type(team['id'])
            if team['id'] == id:
                return team

    def output_user_activity(self):
        """
        retrieve all user activity from server
        """

        url = "%s/api/useractivity" % (self.server,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        useractivity = r.json()

        print "%-12s| %-14s | %-12s | %-5s | %-20s" %("Username", "Timestamp", "Remote Ip", "Result", "Description")
        for attempt in useractivity:
            print "%-12s| %-14s | %-12s | %-5s | %-20s" % (attempt['username'], attempt['timestamp'], attempt['ip_address'], attempt['http_status'], attempt['http_description'])

    def output_user_activity_success(self):
        """
        retrieve all user activity from server and filter out successful attempts
        """

        url = "%s/api/useractivity" % (self.server,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        useractivity = r.json()

        successes = []
        for attempt in useractivity:
            if attempt['http_status'] == 200:
                successes.append(attempt)

        print "%-12s| %-14s | %-12s | %-5s | %-20s" %("Username", "Timestamp", "Remote Ip", "Result", "Description")
        for attempt in successes:
            print "%-12s| %-14s | %-12s | %-5s | %-20s" % (attempt['username'], attempt['timestamp'], attempt['ip_address'], attempt['http_status'], attempt['http_description'])

    def output_user_activity_failure(self):
        """
        retrieve all user activity from server and filter out successful attempts
        """

        url = "%s/api/useractivity" % (self.server,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        useractivity = r.json()

        failures = []
        for attempt in useractivity:
            if attempt['http_status'] == 403:
                failures.append(attempt)

        print "%-12s| %-14s | %-12s | %-5s | %-20s" %("Username", "Timestamp", "Remote Ip", "Result", "Description")
        for attempt in failures:
            print "%-12s| %-14s | %-12s | %-5s | %-20s" % (attempt['username'], attempt['timestamp'], attempt['ip_address'], attempt['http_status'], attempt['http_description'])

    def feed_del(self, id):
        """
        delete a feed, as specified by id
        """
        url = "%s/api/v1/feed/%s" % (self.server, id)

        r = self.cbapi_delete(url)
        r.raise_for_status()

        return r.json()

    def user_del(self,username):


        url = "%s/api/user/%s" % (self.server, username)

        r = self.cbapi_delete(url)
        r.raise_for_status()

        return r.json()

    def feed_modify(self, id, feed):
        """
        updates a watchlist
        """
        url = "%s/api/v1/feed/%s" % (self.server, id)

        r = self.cbapi_put(url, data=json.dumps(feed))
        r.raise_for_status()

        return r.json()

    def feed_synchronize(self, name, full_sync=True):
        """
        force the synchronization of a feed

        this triggers the CB server to refresh the feed.  it does not result in immediate
        tagging of any existing process or binary documents that match the feed.  it does result
        in any new incoming data from sensors being tagged on ingress.
        """

        feed_request = self.cbapi_get("%s/api/v1/feed" % self.server)
        feed_request.raise_for_status()

        for feed in feed_request.json():
            if feed['name'] == name:
                sync_request = self.cbapi_post("%s/api/v1/feed/%s/synchronize" % (self.server, feed["id"]),
                                               data=json.dumps({"full_sync": full_sync}))
                if sync_request.status_code == 200:
                    return {"result": True}
                elif sync_request.status_code == 409:
                    return {"result": False, "reason": "feed disabled"}
                else:
                    raise Exception("Unexpected response from /api/v1/feed/%s/synchronize: %s"
                                    % (feed['id'], sync_request.status_code))

        return {"result": False, "reason": "feed not found"}

    def threat_report_search(self, query_string, start=0, rows=10, sort="severity_score desc"):
        """ Search for threat reports.  Arguments:

            query_string -      The Cb query string; this is the same string used in the
                                "main search box" on the process search page.  "Contains text..."
                                See Cb Query Syntax for a description of options.

            start -             Defaulted to 0.  Will retrieve records starting at this offset.
            rows -              Defaulted to 10. Will retrieve this many rows.
            sort -              Default to last_update desc.  Must include a field and a sort
                                order; results will be sorted by this param.

            Returns a python dictionary with the following primary fields:
                - results - a list of dictionaries describing each matching process
                - total_results - the total number of matches
                - elapsed - how long this search took
                - terms - a list of strings describing how the query was parsed
                - facets - a dictionary of the facet results for this saerch
        """

        # setup the object to be used as the JSON object sent as a payload
        # to the endpoint
        params = {
            'sort': sort,
            'facet': ['true', 'true'],
            'rows': rows,
            'cb.urlver': ['1'],
            'start': start}

        # a q (query) param only needs to be specified if a query is present
        # to search for all processes, provide an empty string for q
        #
        if len(query_string) > 0:
            params['q'] = [query_string]

        # HTTP POST and HTTP GET are both supported for process search
        # HTTP POST allows for longer query strings
        #
        r = self.cbapi_get("%s/api/v1/threat_report" % self.server, params=params)
        r.raise_for_status()
        return r.json()

    def feed_report_info(self, feedid, reportid):
        """
        retrieve a single report from a feed
        """

        url = "%s/api/v1/feed/%s/report/%s" % (self.server, feedid, reportid,)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def feed_report_stats(self, feed_id, report_id):
        """
        Get feed report stats
        """

        url = "%s/api/v1/feed/%s/report/%s/stats" % (self.server, feed_id, report_id)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def feed_action_enum(self,id):
        """
        Gets the actions for a certain feed from the Carbon Black Server
        :param id: the id of the feed
        :return: the actions associated with that feed
        """

        url = "%s/api/v1/feed/%s/action" % (self.server, id)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def feed_action_add(self, id, action_type_id, email_recipient_user_ids):
        """
        enables one of the three pre-determined actions to be performed
        upon hits for feeds: email, create alert, and write to syslog
        :param id: the id of the feed
        :param action_type_id: the id for the type of action
        :param email_recipient_user_ids: ids of users who will be emailed upon a hit
        :return: the added action
        """
        url = "%s/api/v1/feed/%s/action" % (self.server, id)

        request = {
            "action_data": "{\"email_recipients\":[%s]}" % (",".join(str(user_id) for user_id in email_recipient_user_ids)),
            "action_type": action_type_id,
            "group_id": id, #feed id
            "watchlist_id": None
        }

        r = self.cbapi_post(url, data=json.dumps(request))
        r.raise_for_status()
        return r.json()

    def feed_action_update(self, id , action_id, action_type_id):
        """
        updates a feed action
        :param id: the feed id
        :param action_id: the action id
        :param action_type_id: the action type id
        :return: the updated feed
        """
        url = "%s/api/v1/feed/%s/action/%s" % (self.server, id, action_id)

        old_actions = self.feed_action_enum(id)
        for action in old_actions:
            if int(action['id']) == int(action_id):
                curr_action = action

        request = {
            "action_data": curr_action['action_data'],
            "action_type": action_type_id,
            "group_id": curr_action['group_id'],
            "id" : curr_action['id'],
            "watchlist_id": curr_action['watchlist_id']
        }

        r = self.cbapi_put(url, data=json.dumps(request))
        r.raise_for_status()
        return r.json()

    def feed_action_del(self, id, action_id):
        """
        Deletes a feed action
        :param id: the id of the feed
        :param action_id: the id of the action
        :return: whether successful or not
        """
        url =  "%s/api/v1/feed/%s/action/%s" % (self.server, id, action_id)
        r = self.cbapi_delete(url)
        r.raise_for_status()

        return r.json()

    def feed_requirements(self, id):
        """
        Get feed requirements
        """

        url = "%s/api/v1/feed/%s/requirements" % (self.server, id)

        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def alert_search(self, query_string, sort="created_time desc", rows=10, start=0, facet_enable=True):
        """ Search for processes.  Arguments:

            query_string -      The Alert query string; this is the same string used in the
                                "main search box" on the alert search page.  "Contains text..."
                                See Cb Query Syntax for a description of options.

            start -             Defaulted to 0.  Will retrieve records starting at this offset.
            rows -              Defaulted to 10. Will retrieve this many rows.
            sort -              Default to created_time desc.  Must include a field and a sort
                                order; results will be sorted by this param.

            Returns a list of python dictionaries with the following primary fields:
                - results - a list of dictionaries describing each matching process
                - total_results - the total number of matches
                - elapsed - how long this search took
                - terms - a list of strings describing how the query was parsed
                - facets - a dictionary of the facet results for this saerch
        """

        if facet_enable:
            facet_param = ['true', 'true']
        else:
            facet_param = ['false', 'false']

        params = {
            'sort': sort,
            'facet': facet_param,
            'rows': rows,
            'cb.urlver': ['1'],
            'start': start}

        if len(query_string) > 0:
            params['q'] = [query_string]

        r = self.cbapi_get("%s/api/v1/alert" % self.server, params=params)
        r.raise_for_status()
        return r.json()

    def alert_search_iter(self, query_string, sort="created_time desc", start=0, rows=100, facet_enable=True):
        """
        A generator for doing an alert search so you can say for results in alert_search_iter
        so that you can keep iterating through all the results.
        :param query_string:
        :param start:
        :param rows:
        :param sort:
        :return:
        """
        while True:
            resp = self.alert_search(query_string, sort="created_time desc", start=start, rows=rows, facet_enable=True)
            results = resp.get('results')
            for alert in results:
                yield alert
            start += len(results)
            if len(results) < rows:
                break

    def alert_update(self, alert):
        r = self.cbapi_post("%s/api/v1/alert/%s" % (self.server, alert['unique_id']), data=json.dumps(alert))
        r.raise_for_status()
        return r.json()

    def binary_search_iter(self, query_string, start=0, rows=10, **kwargs):
        """
        A generator for doing a binary search so you can say for results in binary_search_iter
        so that you can keep iterating through all the results.
        :param query_string:
        :param start:
        :param rows:
        :param sort:
        :return:
        """
        our_start = start
        while True:
            resp = self.binary_search(query_string, start=our_start, rows=rows, **kwargs)
            results = resp.get('results')
            for binary in results:
                yield binary
            our_start += len(results)
            if len(results) < rows:
                break

    def process_search_iter(self, query_string, start=0, rows=10, **kwargs):
        """
        A generator for doing a process search so you can say for results in process_search_iter
        so that you can keep going through all the results.

        :param cbapi_inst:
        :param query_string:
        :param start:
        :param rows:
        :param sort:
        :return:
        """
        our_start = start
        while True:
            resp = self.process_search(query_string, start=our_start, rows=rows, **kwargs)
            results = resp.get('results')
            for proc in results:
                yield proc
            our_start += len(results)
            if len(results) < rows:
                break

    def process_search_and_detail_iter(self, query):
        """

        :param query:
        :return:
        """
        for proc in self.process_search_iter(query, start=0, rows=200):
            details = self.process_summary(proc.get('id'), proc.get('segment_id'))
            parent_details = details.get('parent')
            proc_details = details.get('process')
            yield (proc, proc_details, parent_details)

    def process_search_and_events_iter(self, query):
        """

        :param query:
        :return:
        """
        for proc in self.process_search_iter(query, start=0, rows=200):
            events = self.process_events(proc['id'], proc['segment_id']).get('process', [])
            yield (proc, events)


    # class ActionType:
    #     Email=0
    #     Syslog=1
    #     HTTPPost=2
    #     Alert=3
    def watchlist_enable_action(self, watchlist_id, action_type=3, action_data=None):
        """
        Enable an action like create an alert, use syslog, or use email on watchlist hit.
        """
        data = {'action_type': action_type}
        if action_data:
            data['action_data'] = action_data
            data['watchlist_id'] = watchlist_id

        url = "%s/api/v1/watchlist/%d/action" % (self.server, watchlist_id)
        r = self.cbapi_post(url, data=json.dumps(data), timeout=120)
        r.raise_for_status()

        return r.json()

    def live_response_session_list(self):
        url = "%s/api/v1/cblr/session" % (self.server)
        r = self.cbapi_get(url, timeout=120)
        r.raise_for_status()
        return r.json()

    def live_response_session_create(self, sensor_id):
        target_session = None
        for session in self.live_response_session_list():
            if int(session.get('sensor_id')) == sensor_id and session.get('status') == "active":
                target_session = session
                break

        if not target_session:
            url = "%s/api/v1/cblr/session" % (self.server)
            data = {"sensor_id": sensor_id}
            r = self.cbapi_post(url, data=json.dumps(data), timeout=120)
            r.raise_for_status()
            target_session = r.json()
        return target_session

    def live_response_session_status(self, session_id):
        url = "%s/api/v1/cblr/session/%d" % (self.server, session_id)
        r = self.cbapi_get(url, timeout=120)
        r.raise_for_status()
        return r.json()

    def live_response_session_command_post(self, session_id, command, command_object=None):
        url = "%s/api/v1/cblr/session/%d/command" % (self.server, session_id)
        data = {"session_id": session_id, "name": command}
        if type(command_object) is list:
            data['object'] = command_object[0]
            data.update(command_object[1])
        else:
            data['object'] = command_object
        r = self.cbapi_post(url, data=json.dumps(data), timeout=120)
        r.raise_for_status()
        return r.json()

    def live_response_session_command_get(self, session_id, command_id, wait=False):
        url = "%s/api/v1/cblr/session/%d/command/%d" % (self.server, session_id, command_id)
        if wait:
            params = {'wait':'true'}
        else:
            params = {}
        r = self.cbapi_get(url, params=params, timeout=120)
        r.raise_for_status()
        return r.json()

    def live_response_session_command_get_file(self, session_id, file_id):
        url = "%s/api/v1/cblr/session/%d/file/%d/content" % (self.server, session_id, file_id)
        r = self.cbapi_get(url, params={}, timeout=120)
        r.raise_for_status()
        return r.content


    def live_response_session_command_put_file(self, session_id, filepath):
        fin = open(filepath, "rb")
        fpost = {'file': fin}

        url = '%s/api/v1/cblr/session/%d/file' % (self.server, session_id)

        headers = {'X-Auth-Token': self.token}

        r = self.cbapi_post(url, files=fpost, timeout=120)

        r.raise_for_status()
        ret = json.loads(r.content)
        fileid = ret["id"]
        return fileid


    def live_response_session_keep_alive(self, session_id):
        url = '%s/api/v1/cblr/session/%d/keepalive' % (self.server, session_id)
        r = self.cbapi_get(url, timeout=120)
        r.raise_for_status()
        return r.json()

    def sensor_toggle_isolation(self, sensor_id, do_isolation):
        data = self.sensor(sensor_id)

        data["network_isolation_enabled"] = do_isolation

        r = self.cbapi_put("%s/api/v1/sensor/%s" % (self.server, sensor_id),
                           data=json.dumps(data), timeout=120)
        r.raise_for_status()
        return r.status_code == 200

    def sensor_flush_current(self, sensor_id):
        # move it forward 1 day because this should get reset regardless once the sensor is current
        flush_time = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 86400))
        return self.sensor_flush(sensor_id, flush_time)

    def sensor_flush(self, sensor_id, flush_time):
        data = self.sensor(sensor_id)
        data["event_log_flush_time"] = flush_time #"Wed, 01 Jan 2020 00:00:00 GMT"

        r = self.cbapi_put("%s/api/v1/sensor/%s" % (self.server, sensor_id),
                           data=json.dumps(data), timeout=120)
        r.raise_for_status()
        return r.status_code == 200

    def move_sensor_to_group(self, sensor_id, new_group_id):
        data = self.sensor(sensor_id)
        data["group_id"] = new_group_id

        r = self.cbapi_put("%s/api/v1/sensor/%s" % (self.server, sensor_id),
                           data=json.dumps(data), timeout=120)
        r.raise_for_status()
        return r.status_code == 200

    def event_add(self, investigation_id, description, start_date):
        """
        Adds a tagged_event to an investigation on the server
        :investigation_id: the id of the investigation to add the event to
        :param description: description of the event
        :param start_date: start date of the event
        :return: the added event
        """
        event_data = {
            'description': description,
        }

        request = {
            'investigation_id': investigation_id,
            'event_data': event_data,
            'start_date': start_date
        }

        url = "%s/api/tagged_event" % self.server

        r = self.cbapi_post(url, data=json.dumps(request))
        r.raise_for_status()

        return r.json()

    def event_info(self, investigation_id):
        """
        Enumerates the tagged_events for a certain investigation and gives their information
        :param id: the id of the investigation this tagged_event is for
        """
        url = "%s/api/tagged_event/%s" % (self.server, investigation_id)
        r = self.cbapi_get(url)
        r.raise_for_status()
        return r.json()

    def event_update(self, id, new_description):
        """
        Updates the description of an event on the server
        :param id: the updated event's investigation id
        :return: the updated event
        """

        #be able to target a single event
        old_event_as_list = self.event_info(id)
        old_event = old_event_as_list[0]
        old_event_data = old_event['event_data']
        new_event_data = {\
            'description' : new_description,\
            }

        request = {\

           'start_date' : old_event['start_date'],\
           'event_data' : {\
                            # set every other event_data field to the old_event value
                            'description' : new_description
                          },\
                  }

        url = "%s/api/tagged_event/%s" % (self.server, id)

        r = self.cbapi_put(url, data=json.dumps(request))
        r.raise_for_status()

        return r.json()

    def event_del(self, id):
        """
        Deletes a tagged_event from the server
        :param id: id of the event to be deleted
        :return: success or failure
        """
        # Way to deal with selecting boxes on the UI
        url = "%s/api/tagged_event/%s" % (self.server, id)
        r = self.cbapi_delete(url)
        r.raise_for_status()

        return r.json()


    def event_by_process_id(self, proc_id):
        """
        Retrieves a tagged_event specified by its process_id
        :param proc_id: the process_id of the event
        :return: the tagged_event
        """

        url = "%s/api/tagged_events/%s" % (self.server, proc_id)
        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def get_builds(self):
        """
        Gets the build versions from the Carbon Black server
        """
        url = "%s/api/builds" % self.server
        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def get_login_caps(self):
        """
        Gets login-caps from Carbon Black server
        """
        url = "%s/api/login-caps" % self.server
        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def group_datasharing_enum(self, group_id):
        """
        Enumerates the datasharing settings for the group with id "group_id"
        from Carbon Black server
        """
        url = "%s/api/v1/group/%s/datasharing" % (self.server, group_id)
        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    # this probably needs something like add_from_data, also look at line
    # that Jeremiah sent you that updated the datasharing settings
    def group_datasharing_add(self, group_id, who, what):
        """
        Add a new datasharing configuration to a sensor group in the CB server
        :param group_id: the sensor group id
        :param what: the type of data being shared i.e. "binaries" or "hashes" etc.
        :param who: What company the data is being shared with
        :return: the added configuration
        """
        request = {
            'group_id': group_id,
            'who': who,
            'what': what,
        }

        url = "%s/api/v1/group/%s/datasharing" % (self.server, group_id)

        r = self.cbapi_post(url, data=json.dumps(request))
        r.raise_for_status()

        return r.json()

    def group_datasharing_del_all(self, group_id):
        """
        Deletes all datasharing configurations for the group with id "group_id"
        from the Carbon Black server
        """
        url = "%s/api/v1/group/%s/datasharing" % (self.server, group_id)
        r = self.cbapi_delete(url)
        r.raise_for_status()

        return r.json()

    def group_datasharing_info(self, group_id, config_id):
        """
        Retrieves a specific datasharing configuration of a sensor group
        :param group_id: id of sensor group
        :param config_id: id of specific datasharing configuration
        :return: the datasharing info for one configuration of a group
        """
        url = "%s/api/v1/group/%s/datasharing/%s" % (self.server,group_id,config_id)
        r = self.cbapi_get(url)
        r.raise_for_status()

        return r.json()

    def group_datasharing_del(self, group_id, config_id):
        """
        Deletes a specific datasharing configuration of a sensor group from the
        Carbon Black server
        :param group_id: id of sensor group
        :param config_id: id of specific datasharing configuration
        :return: the deleted configuration
        """
        url = "%s/api/v1/group/%s/datasharing/%s" % (self.server,group_id,config_id)
        r = self.cbapi_delete(url)
        r.raise_for_status()

        return r.json()

    def cbapi_get(self, url, **kwargs):
        headers = kwargs.pop('headers', None) or self.token_header
        verify_ssl = kwargs.pop('verify', None) or self.ssl_verify
        proxies = kwargs.pop('proxies', None) or self.proxies

        return self.session.get(url, headers=headers, verify=verify_ssl, proxies=proxies, **kwargs)

    def cbapi_post(self, url, **kwargs):
        headers = kwargs.pop('headers', None) or self.token_header
        verify_ssl = kwargs.pop('verify', None) or self.ssl_verify
        proxies = kwargs.pop('proxies', None) or self.proxies

        return self.session.post(url, headers=headers, verify=verify_ssl, proxies=proxies, **kwargs)

    def cbapi_put(self, url, **kwargs):
        headers = kwargs.pop('headers', None) or self.token_header
        verify_ssl = kwargs.pop('verify', None) or self.ssl_verify
        proxies = kwargs.pop('proxies', None) or self.proxies

        return self.session.put(url, headers=headers, verify=verify_ssl, proxies=proxies, **kwargs)

    def cbapi_delete(self, url, **kwargs):
        headers = kwargs.pop('headers', None) or self.token_header
        verify_ssl = kwargs.pop('verify', None) or self.ssl_verify
        proxies = kwargs.pop('proxies', None) or self.proxies

        return self.session.delete(url, headers=headers, verify=verify_ssl, proxies=proxies, **kwargs)
