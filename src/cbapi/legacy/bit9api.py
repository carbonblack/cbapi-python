"""
Python bindings for Bit9Platform API

Copyright Bit9, Inc. 2015 
support@bit9.com

Disclaimer
+++++++++++++++++++
By accessing and/or using the samples scripts provided on this site (the "Scripts"), you hereby agree to the following terms:
The Scripts are examples provided for purposes of illustration only and are not intended to represent specific
recommendations or solutions for API integration activities as use cases can vary widely.
THE SCRIPTS ARE PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED.  BIT9 MAKES NO REPRESENTATION
OR OTHER AFFIRMATION OF FACT, INCLUDING BUT NOT LIMITED TO STATEMENTS REGARDING THE SCRIPTS' SUITABILITY FOR USE OR PERFORMANCE.
IN NO EVENT SHALL BIT9 BE LIABLE FOR SPECIAL, INCIDENTAL, CONSEQUENTIAL, EXEMPLARY OR OTHER INDIRECT DAMAGES OR FOR DIRECT
DAMAGES ARISING OUT OF OR RESULTING FROM YOUR ACCESS OR USE OF THE SCRIPTS, EVEN IF BIT9 IS ADVISED OF OR AWARE OF THE
POSSIBILITY OF SUCH DAMAGES.

"""

import json
import requests
import logging

log = logging.getLogger(__name__)


class bit9Api(object):
    def __init__(self, server, ssl_verify=True, token=None):
        """ Requires:
                server -    URL to the Bit9Platform server.  Usually the same as 
                            the web GUI.
                sslVerify - verify server SSL certificate
                token - this is token for API interface provided by Bit9 administrator
        """

        if not server.startswith("https"): 
            raise TypeError("Server must be URL: e.g, https://bit9server.local")

        if token is None: 
            raise TypeError("Missing required authentication token.")

        self.server = server.rstrip("/")
        if '/api/bit9platform' not in self.server:
            self.server = self.server + '/api/bit9platform'
        self.sslVerify = ssl_verify
        self.tokenHeader = {'X-Auth-Token': token}
        self.tokenHeaderJson = {'X-Auth-Token': token, 'content-type': 'application/json'}

    # Private function that downloads file in chunks
    def __download_file(self, obj_id, obj_name, local_path, chunk_size_kb=10):
        # NOTE the stream=True parameter
        url = self.server + '/' + obj_name + '?id=' + str(obj_id) + '&downloadFile=true'
        r = requests.get(url, headers=self.tokenHeaderJson, verify=self.sslVerify, stream=True)
        r.raise_for_status()
        n = 0
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size_kb*1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
                    n += 1

    def __check_result(self, r):
        if 400 <= r.status_code < 500:
            log.error('%s Client Error: %s, %s' % (r.status_code, r.reason, r.text))
        elif 500 <= r.status_code < 600:
            log.error('%s Server Error: %s, %s' % (r.status_code, r.reason, r.text))
        elif r.text != '':
            return r.json()
        return False

    # Download file from server to the local file system from fileUpload object
    def retrieve_uploaded_file(self, obj_id, local_path):
        return self.__download_file(obj_id, 'v1/fileUpload', local_path)

    # Download file from server to the local file system from pendingAnalysis object
    def retrieve_analyzed_file(self, obj_id, local_path):
        return self.__download_file(obj_id, 'v1/pendingAnalysis', local_path)

    # Retrieve object using HTTP GET request. Note that this function supports searching as well.
    # Optional parameters are obj_id that attempts to retrieve specific object, or url_params that can be used
    # for searching
    def retrieve(self, api_obj, obj_id=0, url_params=''):
        if obj_id:
            api_obj = api_obj + '/' + str(obj_id)
        if url_params:
            url_params = '?' + url_params.lstrip("?")
        url = self.server + '/' + api_obj + url_params
        r = requests.get(url, headers=self.tokenHeaderJson, verify=self.sslVerify)
        return self.__check_result(r)

    # Search object for specific conditions. Optionally sort and/or group results
    # Offset and limit determines the output window in result set.
    # example:
    #       res = bit9.search('v1/computer', ['policyName:development', 'ipAddress!192.168.0.*'], sort='name')
    def search(self, api_obj, search_conditions=[], sort=None, group_by=None, offset=0, limit=1000):
        query = '&q='.join(search_conditions)
        if len(query)>0:
            query = '&q='+query
        if sort and len(sort)>0:
            query = query + '&sort=' + sort
        if group_by and len(group_by)>0:
            query = query + '&group=' + group_by
        query = query + '&offset=' + str(offset) + '&limit=' + str(limit)
        if len(query)>0:
            query = '?'+query.lstrip("&")
        url = self.server + '/' + api_obj + query
        r = requests.get(url, headers=self.tokenHeaderJson, verify=self.sslVerify)
        return self.__check_result(r)

    # Create object using HTTP POST request. Note that this can also be used to update existing object
    def create(self, api_obj, data, url_params=''):
        if not data:
            raise TypeError("Missing object data.")
        if url_params:
            url_params = '?' + url_params.lstrip("?")
        url = self.server + '/' + api_obj + url_params
        r = requests.post(url, data=json.dumps(data), headers=self.tokenHeaderJson, verify=self.sslVerify)
        return self.__check_result(r)
    
    # Update object using HTTP PUT request
    def update(self, api_obj, data, obj_id=0, url_params=''):
        if not data:
            raise TypeError("Missing object data.")
        if url_params:
            url_params = '?' + url_params.lstrip("?")
        if not obj_id:
            obj_id = data['id']
        url = self.server + '/' + api_obj + '/' + str(obj_id) + url_params
        r = requests.put(url, data=json.dumps(data), headers=self.tokenHeaderJson, verify=self.sslVerify)
        return self.__check_result(r)


    # Delete object using HTTP DELETE request.
    def delete(self, api_obj, data=None, obj_id=0, url_params=''):
        if not obj_id and data:
            obj_id = data['id']
        if url_params:
            url_params = '?' + url_params.lstrip("?")
        if not obj_id:
            raise TypeError("Missing object data or id.")
        url = self.server + '/' + api_obj + '/' + str(obj_id) + url_params
        r = requests.delete(url, headers=self.tokenHeaderJson, verify=self.sslVerify)
        return self.__check_result(r)
