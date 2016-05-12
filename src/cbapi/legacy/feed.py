import os
import json
import base64
import re
import time


class CbException(Exception):
    pass

class CbIconError(CbException):
    pass

class CbInvalidFeed(CbException):
    pass

class CbInvalidReport(CbException):
    pass


class CbJSONEncoder(json.JSONEncoder):
    def default(self, o):
        return o.dump()

class CbFeed(object):
    def __init__(self, feedinfo, reports):
        self.data = {'feedinfo': feedinfo,
                     'reports': reports}

    def dump(self, validate=True):
        '''
        dumps the feed data
        :param validate: is set, validates feed before dumping
        :return: json string of feed data
        '''
        if validate:
            self.validate()
        return json.dumps(self.data, cls=CbJSONEncoder, indent=2)

    def __repr__(self):
        return repr(self.data)

    def __str__(self):
        return "CbFeed(%s)" % (self.data.get('feedinfo', "unknown"))

    def iter_iocs(self):
        '''
        yields all iocs in the feed
        '''

        data = json.loads(self.dump(validate=False))
        for report in data["reports"]:
            for md5 in report.get("iocs", {}).get("md5", []):
                yield {"type": "md5", "ioc": md5, "report_id": report.get("id", "")}
            for ip in report.get("iocs", {}).get("ipv4", []):
                yield {"type": "ipv4", "ioc": ip, "report_id": report.get("id", "")}
            for domain in report.get("iocs", {}).get("dns", []):
                yield {"type": "dns", "ioc": domain, "report_id": report.get("id", "")}

    def validate_report_list(self, reports):
        '''
        validates reports as a set, as compared to each report as a standalone entity
        :param reports: list of reports
        '''

        reportids = set()

        # verify that no two reports have the same feed id
        # see CBAPI-17
        for report in reports:
            if report['id'] in reportids:
                raise CbInvalidFeed("duplicate report id '%s'" % report['id']) 
            reportids.add(report['id'])

    def validate(self, pedantic = False, serialized_data=None):
        '''
        validates the feed
        :param pedantic: when set, perform strict validation
        :param serialized_data: serialized data for the feed
        '''
        if not serialized_data:
            # this should be identity, but just to be safe.
            serialized_data = self.dump(validate=False)

        data = json.loads(serialized_data)

        if not "feedinfo" in data:
            raise CbInvalidFeed("Feed missing 'feedinfo' data")

        if not 'reports' in data:
            raise CbInvalidFeed("Feed missing 'reports' structure")

        # validate the feed info
        fi = CbFeedInfo(**data["feedinfo"])
        fi.validate(pedantic = pedantic)

        # validate each report individually
        for rep in data["reports"]:
            report = CbReport(**rep)
            report.validate(pedantic = pedantic)

        # validate the reports as a whole
        self.validate_report_list(data["reports"])

class CbFeedInfo(object):
    def __init__(self, **kwargs):
        # these fields are required in every feed descriptor
        self.required = ["name", "display_name",
                         "summary", "tech_data", "provider_url"]
        self.optional = ["category", "icon", "version", "icon_small"]
        self.noemptystrings = ["name", "display_name", "summary", "tech_data", "category"]
        self.data = kwargs

        # if they are present, set the icon fields of the data to hold
        # the base64 encoded file data from their path
        for icon_field in ["icon", "icon_small"]:
            if icon_field in self.data and os.path.exists(self.data[icon_field]):
                icon_path = self.data.pop(icon_field)
                try:
                    self.data[icon_field] = base64.b64encode(open(icon_path, "rb").read())
                except Exception, err:
                    raise CbIconError("Unknown error reading/encoding icon data: %s" % err)

    def dump(self):
        '''
        validates, then dumps the feed info data
        :return: the feed info data
        '''
        self.validate()
        return self.data

    def validate(self, pedantic = False):
        """ a set of checks to validate data before we export the feed"""

        if not all([x in self.data.keys() for x in self.required]):
            missing_fields = ", ".join(set(self.required).difference(set(self.data.keys())))
            raise CbInvalidFeed("FeedInfo missing required field(s): %s" % missing_fields)

        # verify no non-supported keys are present
        for key in self.data.keys():
            if key not in self.required and key not in self.optional:
                raise CbInvalidFeed("FeedInfo includes extraneous key '%s'" % key)

        # check to see if icon_field can be base64 decoded
        for icon_field in ["icon", "icon_small"]:
            try:
                base64.b64decode(self.data[icon_field])
            except TypeError, err:
                raise CbIconError("Icon must either be path or base64 data.  \
                                        Path does not exist and base64 decode failed with: %s" % err)
            except KeyError as err:
                # we don't want to cause a ruckus if the icon is missing
                pass

        # all fields in feedinfo must be strings
        for key in self.data.keys():
            if not (isinstance(self.data[key], unicode) or isinstance(self.data[key], str)):
                raise CbInvalidFeed("FeedInfo field %s must be of type %s, the field \
                                    %s is of type %s " % (key, "unicode", key, type(self.data[key])))

        # certain fields, when present, must not be empty strings
        for key in self.data.keys():
            if key in self.noemptystrings and self.data[key] == "":
                raise CbInvalidFeed("The '%s' field must not be an empty string" % key)

        # validate shortname of this field is just a-z and 0-9, with at least one character
        if not self.data["name"].isalnum():
            raise CbInvalidFeed(
                "Feed name %s may only contain a-z, A-Z, 0-9 and must have one character" % self.data["name"])
        
        return True

    def __str__(self):
        return "CbFeed(%s)" % (self.data.get("name", "unnamed"))

    def __repr__(self):
        return repr(self.data)


class CbReport(object):
    def __init__(self, allow_negative_scores=False, **kwargs):

        # negative scores introduced in CB 4.2
        # negative scores indicate a measure of "goodness" versus "badness"
        self.allow_negative_scores = allow_negative_scores

        # these fields are required in every report
        self.required = ["iocs", "timestamp", "link", "title", "id", "score"]

        # these fields must be of type string
        self.typestring = ["link", "title", "id", "description"]

        # these fields must be of type int
        self.typeint = ["timestamp", "score"]

        # these fields are optional
        self.optional = ["tags", "description"]

        # valid IOC types are "md5", "ipv4", "dns", "query"
        self.valid_ioc_types = ["md5", "ipv4", "dns", "query"]

        # valid index_type options for "query" IOC
        self.valid_query_ioc_types = ["events", "modules"]

        if "timestamp" not in kwargs:
            kwargs["timestamp"] = int(time.mktime(time.gmtime()))

        self.data = kwargs

    def dump(self):
        self.validate()
        return self.data

    def is_valid_query(self, q, reportid):
        """
        make a determination as to if this is a valid query
        """
        # the query itself must be percent-encoded
        # verify there are only non-reserved characters present
        # no logic to detect unescaped '%' characters
        for c in q:
            if c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~%*()":
                raise CbInvalidReport("Unescaped non-reserved character '%s' found in query for report %s; use percent-encoding" % (c, reportid))
 
    def validate(self, pedantic = False):
        """ a set of checks to validate the report"""

        # validate we have all required keys
        global ip
        if not all([x in self.data.keys() for x in self.required]):
            missing_fields = ", ".join(set(self.required).difference(set(self.data.keys())))
            raise CbInvalidReport("Report missing required field(s): %s" % missing_fields)

        # validate that no extra keys are present
        for key in self.data.keys():
            if key not in self.required and key not in self.optional:
                raise CbInvalidReport("Report contains extra key '%s'" % key)

        # (pedantically) validate only required keys are present
        if pedantic and len(self.data.keys()) > len(self.required):
            raise CbInvalidReport("Report contains extra keys: %s" %
                                  (set(self.data.keys()) - set(self.required)))

        # CBAPI-36
        # verify that all fields that should be strings are strings
        for key in self.typestring:
            if key in self.data.keys():
                if not isinstance(self.data[key], basestring):
                    raise CbInvalidReport("Report field '%s' must be a string" % key)

        # verify that all fields that should be ints are ints
        for key in self.typeint:
            if key in self.data.keys():
                if not isinstance(self.data[key], int):
                    raise CbInvalidReport("Report field '%s' must be an int" % key)

        # validate that tags is a list of alphanumeric strings
        if "tags" in self.data.keys():
            if type(self.data["tags"]) != type([]):
                raise CbInvalidReport("Tags must be a list")
            for tag in self.data["tags"]:
                if not str(tag).isalnum():
                    raise CbInvalidReport("Tag '%s' is not alphanumeric" % tag)
                if len(tag) > 32:
                    raise CbInvalidReport("Tags must be 32 characters or fewer") 
        
        # validate score is integer between -100 (if so specified) or 0 and 100
        try:
            int(self.data["score"])
        except ValueError:
            raise CbInvalidReport(
                "Report has non-integer score %s in report %s" % (self.data["score"], self.data["id"]))

        if self.data["score"] < -100 or self.data["score"] > 100:
            raise CbInvalidReport(
                "Report score %s out of range -100 to 100 in report %s" % (self.data["score"], self.data["id"]))

        if not self.allow_negative_scores and self.data["score"] < 0:
            raise CbInvalidReport(
                "Report score %s out of range 0 to 100 in report %s" % (self.data["score"], self.data["id"]))

        # validate id of this report is just a-z and 0-9 and - and ., with at least one character
        if not re.match("^[a-zA-Z0-9-_.]+$", self.data["id"]):
            raise CbInvalidReport(
                "Report ID  %s may only contain a-z, A-Z, 0-9, - and must have one character" % self.data["id"])

        # validate there is at least one IOC for each report and each IOC entry has at least one entry
        if not all([len(self.data["iocs"][ioc]) >= 1 for ioc in self.data['iocs']]):
            raise CbInvalidReport("Report IOC list with zero length in report %s" % (self.data["id"]))

        # convenience variable 
        iocs = self.data['iocs']

        # validate that there are at least one type of ioc present
        if len(iocs.keys()) == 0:
            raise CbInvalidReport("Report with no IOCs in report %s" % (self.data["id"]))

        # (pedantically) validate that no extra keys are present
        if pedantic and len(set(iocs.keys()) - set(self.valid_ioc_types)) > 0:
            raise CbInvalidReport(
                "Report IOCs section contains extra keys: %s" % (set(iocs.keys()) - set(self.valid_ioc_types)))

        # Let us check and make sure that for "query" ioc type does not contain other types of ioc
        query_ioc = "query" in iocs.keys()
        if query_ioc and len(iocs.keys()) > 1:
            raise CbInvalidReport(
                "Report IOCs section for \"query\" contains extra keys: %s for report %s" %
                (set(iocs.keys()), self.data["id"]))
        
        if query_ioc:
            iocs_query = iocs["query"][0]
           
            # validate that the index_type field exists 
            if "index_type" not in iocs_query.keys():
                raise CbInvalidReport("Query IOC section for report %s missing index_type" % self.data["id"])
            
            # validate that the index_type is a valid value
            if not iocs_query.get("index_type", None) in self.valid_query_ioc_types:
                raise CbInvalidReport(
                    "Report IOCs section for \"query\" contains invalid index_type: %s for report %s" %
                    (iocs_query.get("index_type", None), self.data["id"]))

            # validate that the search_query field exists 
            if "search_query" not in iocs_query.keys():
                raise CbInvalidReport("Query IOC for report %s missing 'search_query'" % self.data["id"])

            # validate that the search_query field is at least minimally valid
            # in particular, we are looking for a "q=" or "cb.q."
            # this is by no means a complete validation, but it does provide a protection
            # against leaving the actual query unqualified
            if "q=" not in iocs_query["search_query"] and "cb.q." not in iocs_query["search_query"]:
                raise CbInvalidReport("Query IOC for report %s missing q= on query" % self.data["id"])

            for kvpair in iocs_query["search_query"].split('&'):
              if 2 != len(kvpair.split('=')):
                  continue
              if kvpair.split('=')[0] == 'q':
                  self.is_valid_query(kvpair.split('=')[1], self.data["id"])

        # validate all md5 fields are 32 characters, just alphanumeric, and 
        # do not include [g-z] and [G-Z] meet the alphanumeric criteria but are not valid in a md5
        for md5 in iocs.get("md5", []):
            if 32 != len(md5):
                raise CbInvalidReport("Invalid md5 length for md5 (%s) for report %s" % (md5, self.data["id"]))
            if not md5.isalnum():
                raise CbInvalidReport("Malformed md5 (%s) in IOC list for report %s" % (md5, self.data["id"]))
            for c in "ghijklmnopqrstuvwxyz":
                if c in md5 or c.upper() in md5:
                    raise CbInvalidReport("Malformed md5 (%s) in IOC list for report %s" % (md5, self.data["id"]))

                    # validate all IPv4 fields pass socket.inet_ntoa()
        import socket

        try:
            [socket.inet_aton(ip) for ip in iocs.get("ipv4", [])]
        except socket.error:
            raise CbInvalidReport("Malformed IPv4 (%s) addr in IOC list for report %s" % (ip, self.data["id"]))

        # validate all lowercased domains have just printable ascii
        import string
        # 255 chars allowed in dns; all must be printables, sans control characters
        # hostnames can only be A-Z, 0-9 and - but labels can be any printable.  See 
        # O'Reilly's DNS and Bind Chapter 4 Section 5: 
        # "Names that are not host names can consist of any printable ASCII character."
        allowed_chars = string.printable[:-6]
        for domain in iocs.get("dns", []):
            if len(domain) > 255:
                raise CbInvalidReport(
                    "Excessively long domain name (%s) in IOC list for report %s" % (domain, self.data["id"]))
            if not all([c in allowed_chars for c in domain]):
                raise CbInvalidReport(
                    "Malformed domain name (%s) in IOC list for report %s" % (domain, self.data["id"]))
            labels = domain.split('.')
            if 0 == len(labels):
                raise CbInvalidReport("Empty domain name in IOC list for report %s" % (self.data["id"]))
            for label in labels:
                if len(label) < 1 or len(label) > 63:
                    raise CbInvalidReport("Invalid label length (%s) in domain name (%s) for report %s" % (
                        label, domain, self.data["id"]))

        return True

    def __str__(self):
        return "CbReport(%s)" % (self.data.get("title", self.data.get("id", '')) )

    def __repr__(self):
        return repr(self.data)
