"""Parses STIX observables from the XML data returned by the TAXII server.

The following IOC types are extracted from STIX data:

* MD5 Hashes
* Domain Names
* IP-Addresses
* IP-Address Ranges
"""

from cybox.objects.domain_name_object import DomainName
from cybox.objects.address_object import Address
from cybox.objects.file_object import File
from cybox.objects.uri_object import URI
from lxml import etree
from io import BytesIO
from stix.core import STIXPackage

import logging
import string
import socket
import uuid
import time
import datetime
import dateutil
import dateutil.tz
import re

from cabby.constants import (
    CB_STIX_XML_111, CB_CAP_11, CB_SMIME,
    CB_STIX_XML_10, CB_STIX_XML_101, CB_STIX_XML_11, CB_XENC_122002)

CB_STIX_XML_12 = 'urn:stix.mitre.org:xml:1.2'

BINDING_CHOICES = [CB_STIX_XML_111, CB_CAP_11, CB_SMIME, CB_STIX_XML_12,
                   CB_STIX_XML_10, CB_STIX_XML_101, CB_STIX_XML_11,
                   CB_XENC_122002]


logger = logging.getLogger(__name__)


domain_allowed_chars = string.printable[:-6]  # Used by validate_domain_name function


def validate_domain_name(domain_name):
    """Validates a domain name to ensure validity and saneness.

    Args:
        domain_name: Domain name string to check.

    Returns:
        True if checks pass, False otherwise.
    """

    if len(domain_name) > 255:
        logger.warn(
            "Excessively long domain name {} in IOC list".format(domain_name))
        return False

    if not all([c in domain_allowed_chars for c in domain_name]):
        logger.warn("Malformed domain name {} in IOC list".format(domain_name))
        return False

    parts = domain_name.split('.')
    if not parts:
        logger.warn("Empty domain name found in IOC list")
        return False

    for part in parts:
        if len(part) < 1 or len(part) > 63:
            logger.warn("Invalid label length {} in domain name {} for report %s".format(
                part, domain_name))
            return False

    return True


def validate_md5sum(md5):
    """Validates md5sum.

    Args:
        md5sum: md5sum to check.

    Returns:
        True if checks pass, False otherwise.
    """

    if 32 != len(md5):
        logger.warn("Invalid md5 length for md5 {}".format(md5))
        return False
    if not md5.isalnum():
        logger.warn("Malformed md5 {} in IOC list".format(md5))
        return False
    for c in "ghijklmnopqrstuvwxyz":
        if c in md5 or c.upper() in md5:
            logger.warn("Malformed md5 {} in IOC list".format(md5))
            return False

    return True


def sanitize_id(id):
    """Removes unallowed chars from an ID.

    Ids may only contain a-z, A-Z, 0-9, - and must have one character.

    Args:
        id: the ID to be sanitized.

    Returns:
        A sanitized ID.
    """

    return id.replace(':', '-')


def validate_ip_address(ip_address):
    """Validates an IPv4 address."""

    try:
        socket.inet_aton(ip_address)
        return True
    except socket.error:
        return False


def cybox_parse_observable(observable, indicator, timestamp, score):
    """Parses a cybox observable and returns a list containing a report dictionary.

    cybox is a open standard language encoding info about cyber observables.

    Args:
        observable: the cybox obserable to parse.

    Returns:
        A report dictionary if the cybox observable has props of type:

            cybox.objects.address_object.Address,
            cybox.objects.file_object.File,
            cybox.objects.domain_name_object.DomainName, or
            cybox.objects.uri_object.URI

        Otherwise it will return an empty list.

    """
    reports = []

    if observable.object_ and observable.object_.properties:
        props = observable.object_.properties
        logger.debug("{0} has props type: {1}".format(indicator, type(props)))
    else:
        logger.debug("{} has no props; skipping".format(indicator))
        return reports

    #
    # sometimes the description is None
    #
    description = ''
    if observable.description and observable.description.value:
        description = str(observable.description.value)

    #
    # if description is an empty string, then use the indicator's description
    # NOTE: This was added for RecordedFuture
    #

    if not description and indicator and indicator.description and indicator.description.value:
        description = str(indicator.description.value)

    #
    # if description is still empty, use the indicator's title
    #
    if not description and indicator and indicator.title:
        description = str(indicator.title)

    #
    # use the first reference as a link
    # This was added for RecordedFuture
    #
    link = ''
    if indicator and indicator.producer and indicator.producer.references:
        for reference in indicator.producer.references:
            link = reference
            break
    else:
        if indicator and indicator.title:
            split_title = indicator.title.split()
            title_found = True
        elif observable and observable.title:
            split_title = observable.title.split()
            title_found = True
        else:
            title_found = False

        if title_found:
            url_pattern = re.compile("^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$")
            for token in split_title:
                if url_pattern.match(token):
                    link = token
                    break


    #
    # Sometimes the title is None, so generate a random UUID
    #

    if observable and observable.title:
        title = observable.title
    else:
        title = str(uuid.uuid4())

    # ID must be unique. Collisions cause 500 error on Carbon Black backend
    id = str(uuid.uuid4())

    if type(props) == DomainName:
        # go into domainname function
        reports = parse_domain_name_observable(observable, props, id, description, title, timestamp, link, score)

    elif type(props) == Address:
        reports = parse_address_observable(observable, props, id, description, title, timestamp, link, score)

    elif type(props) == File:
        reports = parse_file_observable(observable, props, id, description, title, timestamp, link, score)

    elif type(props) == URI:
        reports = parse_uri_observable(observable, props, id, description, title, timestamp, link, score)

    else:
        return reports

    return reports

def parse_uri_observable(observable, props, id, description, title, timestamp, link, score):

    reports = []

    if props.value and props.value.value:

        iocs = {'netconn_domain': []}
        #
        # Sometimes props.value.value is a list
        #

        if type(props.value.value) is list:
            for domain_name in props.value.value:
                if validate_domain_name(domain_name.strip()):
                    iocs['netconn_domain'].append(domain_name.strip())
        else:
            domain_name = props.value.value.strip()
            if validate_domain_name(domain_name):
                iocs['netconn_domain'].append(domain_name)

        if len(iocs['netconn_domain']) > 0:
            reports.append({'iocs_v2': iocs,
                            'id': sanitize_id(id),
                            'description': description,
                            'title': title,
                            'timestamp': timestamp,
                            'link': link,
                            'score': score})
    return reports


def parse_domain_name_observable(observable, props, id, description, title, timestamp, link, score):

    reports = []
    if props.value and props.value.value:
        iocs = {'netconn_domain': []}
        #
        # Sometimes props.value.value is a list
        #

        if type(props.value.value) is list:
            for domain_name in props.value.value:
                if validate_domain_name(domain_name.strip()):
                    iocs['netconn_domain'].append(domain_name.strip())
        else:
            domain_name = props.value.value.strip()
            if validate_domain_name(domain_name):
                iocs['netconn_domain'].append(domain_name)

        if len(iocs['netconn_domain']) > 0:
            reports.append({'iocs_v2': iocs,
                            'id': sanitize_id(id),
                            'description': description,
                            'title': title,
                            'timestamp': timestamp,
                            'link': link,
                            'score': score})
    return reports


def parse_address_observable(observable, props, id, description, title, timestamp, link, score):

    reports = []
    if props.category == 'ipv4-addr' and props.address_value:
        iocs = {'netconn_ipv4': []}

        #
        # Sometimes props.address_value.value is a list vs a string
        #
        if type(props.address_value.value) is list:
            for ip in props.address_value.value:
                if validate_ip_address(ip.strip()):
                    iocs['netconn_ipv4'].append(ip.strip())
        else:
            ipv4 = props.address_value.value.strip()
            if validate_ip_address(ipv4):
                iocs['netconn_ipv4'].append(ipv4)

        if len(iocs['netconn_ipv4']) > 0:
            reports.append({'iocs_v2': iocs,
                            'id': sanitize_id(observable.id_),
                            'description': description,
                            'title': title,
                            'timestamp': timestamp,
                            'link': link,
                            'score': score})

    return reports


def parse_file_observable(observable, props, id, description, title, timestamp, link, score):

    reports = []
    iocs = {'hash': []}
    if props.md5:
        if type(props.md5) is list:
            for hash in props.md5:
                if validate_md5sum(hash.strip()):
                    iocs['hash'].append(hash.strip())
        else:
            if hasattr(props.md5, 'value'):
                hash = props.md5.value.strip()
            else:
                hash = props.md5.strip()
            if validate_md5sum(hash):
                iocs['hash'].append(hash)

        if len(iocs['hash']) > 0:
            reports.append({'iocs_v2': iocs,
                            'id': sanitize_id(id),
                            'description': description,
                            'title': title,
                            'timestamp': timestamp,
                            'link': link,
                            'score': score})

    return reports


def get_stix_indicator_score(indicator, default_score):
    """Returns a digit representing the indicator score.

    Converts from "high", "medium", or "low" into a digit, if necessary.
    """

    if not indicator.confidence:
        return default_score


    confidence_val_str = indicator.confidence.value.__str__()
    if confidence_val_str.isdigit():
        score = int(confidence_val_str)
        return score
    elif confidence_val_str.lower() == "high":
        return 7  # 75
    elif confidence_val_str.lower() == "medium":
        return 5  # 50
    elif confidence_val_str.lower() == "low":
        return 2  # 25
    else:
        return default_score


def get_stix_indicator_timestamp(indicator):
    timestamp = 0
    if indicator.timestamp:
        if indicator.timestamp.tzinfo:
            timestamp = int((indicator.timestamp -
                            datetime.datetime(1970, 1, 1).replace(
                                tzinfo=dateutil.tz.tzutc())).total_seconds())
        else:
            timestamp = int((indicator.timestamp -
                            datetime.datetime(1970, 1, 1)).total_seconds())
    return timestamp


def get_stix_package_timestamp(stix_package):
    timestamp = 0
    if not stix_package or not stix_package.timestamp:
        return timestamp
    try:
        timestamp = stix_package.timestamp
        timestamp = int(time.mktime(timestamp.timetuple()))
    except (TypeError, OverflowError, ValueError) as e:
        logger.warning("Problem parsing stix timestamp: {}".format(e))
    return timestamp


def parse_stix_indicators(stix_package, default_score):
    reports = []
    if not stix_package.indicators:
        return reports

    for indicator in stix_package.indicators:
        if not indicator or not indicator.observable:
            continue
        score = get_stix_indicator_score(indicator, default_score)
        timestamp = get_stix_indicator_timestamp(indicator)
        yield from cybox_parse_observable(
            indicator.observable, indicator, timestamp, score)


def parse_stix_observables(stix_package, default_score):
    reports = []
    if not stix_package.observables:
        return reports

    timestamp = get_stix_package_timestamp(stix_package)
    for observable in stix_package.observables:
        if not observable:
            continue
        yield from cybox_parse_observable(              # single element list
            observable, None, timestamp, default_score)


def sanitize_stix(stix_xml):
    ret_xml = b''
    try:
        xml_root = etree.fromstring(stix_xml)
        content = xml_root.find(
            './/{http://taxii.mitre.org/messages/taxii_xml_binding-1.1}Content')
        if content is not None and len(content) == 0 and len(list(content)) == 0:
            # Content has no children.
            # So lets make sure we parse the xml text for content and
            # re-add it as valid XML so we can parse
            _content = xml_root.find(
                "{http://taxii.mitre.org/messages/taxii_xml_binding-1.1}Content_Block/{http://taxii.mitre.org/messages/taxii_xml_binding-1.1}Content")
            if _content:
                new_stix_package = etree.fromstring(_content.text)
                content.append(new_stix_package)
        ret_xml = etree.tostring(xml_root)
    except etree.ParseError as e:
        logger.warning("Problem parsing stix: {}".format(e))
    return ret_xml


def parse_stix(stix_xml, default_score):
    reports = []
    try:
        stix_xml = sanitize_stix(stix_xml)
        bio = BytesIO(stix_xml)
        stix_package = STIXPackage.from_xml(bio)
        if not stix_package:
            logger.warning("Could not parse STIX xml")
            return reports
        if not stix_package.indicators and not stix_package.observables:
            logger.info("No indicators or observables found in stix_xml")
            return reports
        yield from parse_stix_indicators(stix_package, default_score)
        yield from parse_stix_observables(stix_package, default_score)
    except etree.XMLSyntaxError as e:
        logger.warning("Problem parsing stix: {}".format(e))
        return reports
