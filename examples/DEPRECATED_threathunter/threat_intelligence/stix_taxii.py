"""Connects to TAXII servers via cabby and formats the data received for dispatching to a Carbon Black feed."""

import argparse
import logging
import traceback
from threatintel import ThreatIntel
from cabby.exceptions import NoURIProvidedError, ClientException
from requests.exceptions import ConnectionError
from cbapi.errors import ApiError
from cabby import create_client
from dataclasses import dataclass
import yaml
import os
from stix_parse import parse_stix, BINDING_CHOICES
from feed_helper import FeedHelper
from datetime import datetime
from results import AnalysisResult
from cbapi.psc.threathunter.models import Feed
import urllib3
import copy

# logging.basicConfig(filename='stix.log', filemode='w', level=logging.DEBUG)
logging.basicConfig(filename='stix.log', filemode='w', format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO)
handled_exceptions = (NoURIProvidedError, ClientException, ConnectionError)


def load_config_from_file():
    """Loads YAML formatted configuration from config.yml in working directory."""

    logging.debug("loading config from file")
    config_filename = os.path.join(os.path.dirname((os.path.abspath(__file__))), "config.yml")
    with open(config_filename, "r") as config_file:
        config_data = yaml.load(config_file, Loader=yaml.SafeLoader)
        config_data_without_none_vals = copy.deepcopy(config_data)
        for site_name, site_config_dict in config_data['sites'].items():
            for conf_key, conf_value in site_config_dict.items():
                if conf_value is None:
                    del config_data_without_none_vals['sites'][site_name][conf_key]
        logging.info(f"loaded config data: {config_data_without_none_vals}")
        return config_data_without_none_vals


@dataclass(eq=True, frozen=True)
class TaxiiSiteConfig:
    """Contains information needed to interface with a TAXII server.

    These values are loaded in from config.yml for each entry in the configuration file.
    Each TaxiiSiteConnector has its own TaxiiSiteConfig.
    """

    feed_id: str = ''
    site: str = ''
    discovery_path: str = ''
    collection_management_path: str = ''
    poll_path: str = ''
    use_https: bool = True
    ssl_verify: bool = True
    cert_file: str = None
    key_file: str = None
    default_score: int = 5  # [1,10]
    username: str = None
    password: str = None
    collections: str = '*'
    start_date: str = None
    size_of_request_in_minutes: int = 1440
    ca_cert: str = None
    http_proxy_url: str = None
    https_proxy_url: str = None
    reports_limit: int = None
    fail_limit: int = 10   # num attempts per collection for polling & parsing


class TaxiiSiteConnector():
    """Connects to and pulls data from a TAXII server."""

    def __init__(self, site_conf):
        self.config = TaxiiSiteConfig(**site_conf)
        self.client = None

    def create_taxii_client(self):
        """Connects to a TAXII server using cabby and configuration entries."""

        conf = self.config
        if not conf.start_date:
            logging.error(f"A start_date is required for site {conf.site}. Exiting.")
            return
        if not conf.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            client = create_client(conf.site,
                                   use_https=conf.use_https,
                                   discovery_path=conf.discovery_path)
            client.set_auth(username=conf.username,
                            password=conf.password,
                            verify_ssl=conf.ssl_verify,
                            ca_cert=conf.ca_cert,
                            cert_file=conf.cert_file,
                            key_file=conf.key_file)

            proxy_dict = dict()
            if conf.http_proxy_url:
                proxy_dict['http'] = conf.http_proxy_url
            if conf.https_proxy_url:
                proxy_dict['https'] = conf.https_proxy_url
            if proxy_dict:
                client.set_proxies(proxy_dict)

            self.client = client

        except handled_exceptions as e:
            logging.error(f"Error creating client: {e}")

    def create_uri(self, config_path):
        """Formats a URI for discovery, collection, or polling of a TAXII server.

        Args:
            config_path: A URI path to a TAXII server's discovery, collection, or polling service. Defined in config.yml configuration file.

        Returns:
            A full URI to one of a TAXII server's service paths.
        """

        uri = None
        if self.config.site and config_path:
            if self.config.use_https:
                uri = 'https://'
            else:
                uri = 'http://'
            uri = uri + self.config.site + config_path
        return uri

    def query_collections(self):
        """Returns a list of STIX collections available to the user to poll."""

        collections = []
        try:
            uri = self.create_uri(self.config.collection_management_path)
            collections = self.client.get_collections(
                uri=uri)  # autodetect if uri=None
            for collection in collections:
                logging.info(f"Collection: {collection.name}, {collection.type}")
        except handled_exceptions as e:
            logging.warning(f"Problem fetching collections from TAXII server. Check your TAXII Provider URL and username/password (if required to access TAXII server): {e}")
        return collections

    def poll_server(self, collection, feed_helper):
        """Returns a STIX content block for a specific TAXII collection.

        Args:
            collection: Name of a TAXII collection to poll.
            feed_helper: FeedHelper object.
        """

        content_blocks = []
        uri = self.create_uri(self.config.poll_path)
        try:
            logging.info(f"Polling Collection: {collection.name}")
            content_blocks = self.client.poll(
                uri=uri,
                collection_name=collection.name,
                begin_date=feed_helper.start_date,
                end_date=feed_helper.end_date,
                content_bindings=BINDING_CHOICES)
        except handled_exceptions as e:
            logging.warning(f"problem polling taxii server: {e}")
        return content_blocks

    def parse_collection_content(self, content_blocks):
        """Yields a formatted report dictionary for each STIX content_block.

        Args:
            content_block: A chunk of STIX data from the TAXII collection being polled.
        """

        for block in content_blocks:
            yield from parse_stix(block.content, self.config.default_score)

    def import_collection(self, collection):
        """Polls a single TAXII server collection.

        Starting at the start_date set in config.yml, a FeedHelper object will continue to grab chunks
        of data from a collection until the report limit is reached or we reach the current datetime.

        Args:
            collection: Name of a TAXII collection to poll.

        Yields:
            Formatted report dictionaries from parse_collection_content(content_blocks)
            for each content_block pulled from a single TAXII collection.
        """

        num_times_empty_content_blocks = 0
        advance = True
        reports_limit = self.config.reports_limit
        if not self.config.size_of_request_in_minutes:
            size_of_request_in_minutes = 1440
        else:
            size_of_request_in_minutes = self.config.size_of_request_in_minutes
        feed_helper = FeedHelper(self.config.start_date,
                                 size_of_request_in_minutes)
        # config parameters `start_date` and `size_of_request_in_minutes` tell this Feed Helper
        # where to start polling in the collection, and then will advance polling in chunks of
        # `size_of_request_in_minutes` until we hit the most current `content_block`,
        # or reports_limit is reached.
        while feed_helper.advance():
            num_reports = 0
            num_times_empty_content_blocks = 0
            content_blocks = self.poll_server(collection, feed_helper)
            reports = self.parse_collection_content(content_blocks)
            for report in reports:
                yield report
                num_reports += 1
                if reports_limit is not None and num_reports >= reports_limit:
                    logging.info(f"Reports limit of {self.config.reports_limit} reached")
                    advance = False
                    break

            if not advance:
                break
            if collection.type == 'DATA_SET':  # data is unordered, not a feed
                logging.info(f"collection:{collection}; type data_set; breaking")
                break
            if num_reports == 0:
                num_times_empty_content_blocks += 1
            if num_times_empty_content_blocks > self.config.fail_limit:
                logging.error('Max fail limit reached; Exiting.')
                break
            if reports_limit is not None:
                reports_limit -= num_reports

    def import_collections(self, available_collections):
        """Polls each desired collection specified in config.yml.

        Args:
            available_collections: list of collections available to a TAXII server user.

        Yields:
            From import_collection(self, collection) for each desired collection.
        """

        if not self.config.collections:
            desired_collections = '*'
        else:
            desired_collections = self.config.collections

        desired_collections = [x.strip()
                               for x in desired_collections.lower().split(',')]

        want_all = True if '*' in desired_collections else False

        for collection in available_collections:
            if collection.type != 'DATA_FEED' and collection.type != 'DATA_SET':
                logging.debug(f"collection:{collection}; type not feed or data")
                continue
            if not collection.available:
                logging.debug(f"collection:{collection} not available")
                continue
            if want_all or collection.name.lower() in desired_collections:
                yield from self.import_collection(collection)

    def generate_reports(self):
        """Returns a list of report dictionaries for each desired collection specified in config.yml."""

        reports = []

        self.create_taxii_client()
        if not self.client:
            logging.error('Unable to create taxii client.')
            return reports

        available_collections = self.query_collections()
        if not available_collections:
            logging.warning('Unable to find any collections.')
            return reports

        reports = self.import_collections(available_collections)
        if not reports:
            logging.warning('Unable to import collections.')
            return reports

        return reports


class StixTaxii():
    """Allows for interfacing with multiple TAXII servers.

    Instantiates separate TaxiiSiteConnector objects for each site specified in config.yml.
    Formats report dictionaries into AnalysisResult objects with formatted IOC_v2 attirbutes.
    Sends AnalysisResult objects to ThreatIntel.push_to_cb for dispatching to a feed.
    """

    def __init__(self, site_confs):
        self.config = site_confs
        self.client = None

    def result(self, **kwargs):
        """Returns a new AnalysisResult with the given fields populated."""

        result = AnalysisResult(**kwargs).normalize()
        return result

    def configure_sites(self):
        """Creates a TaxiiSiteConnector for each site in config.yml"""

        self.sites = {}
        try:
            for site_name, site_conf in self.config['sites'].items():
                self.sites[site_name] = TaxiiSiteConnector(site_conf)
                logging.info(f"loaded site {site_name}")
        except handled_exceptions as e:

            logging.error(f"Error in parsing config file: {e}")

    def format_report(self, reports):
        """Converts a dictionary into an AnalysisResult.

        Args:
            reports: list of report dictionaries containing an id, title, description, timestamp, score, link, and iocs_v2.

        Yields:
            An AnalysisResult for each report dictionary.
        """

        for report in reports:
            try:
                analysis_name = report['id']
                title = report['title']
                description = report['description']
                scan_time = datetime.fromtimestamp(report['timestamp'])
                score = report['score']
                link = report['link']
                ioc_dict = report['iocs_v2']
                result = self.result(
                                     analysis_name=analysis_name,
                                     scan_time=scan_time,
                                     score=score,
                                     title=title,
                                     description=description)
                for ioc_key, ioc_val in ioc_dict.items():
                    result.attach_ioc_v2(values=ioc_val, field=ioc_key, link=link)
            except handled_exceptions as e:
                logging.warning(f"Problem in report formatting: {e}")
                result = self.result(
                    analysis_name="exception_format_report", error=True)
            yield result

    def collect_and_send_reports(self):
        """Collects and sends formatted reports to ThreatIntel.push_to_cb for validation and dispatching to a feed."""

        self.configure_sites()
        ti = ThreatIntel()
        for site_name, site_conn in self.sites.items():
            logging.debug(f"Verifying Feed {site_conn.config.feed_id} exists")
            try:
                ti.verify_feed_exists(site_conn.config.feed_id)
            except ApiError as e:
                logging.error(f"Couldn't find CbTH Feed {site_conn.config.feed_id}. Skipping {site_name}: {e}")
                continue
            logging.info(f"Talking to {site_name} server")
            reports = site_conn.generate_reports()
            if not reports:
                logging.error(f"No reports generated for {site_name}")
                continue
            else:
                try:
                    ti.push_to_cb(feed_id=site_conn.config.feed_id, results=self.format_report(reports))
                except Exception as e:
                    logging.error(traceback.format_exc())
                    logging.error(f"Failed to push reports to feed {site_conn.config.feed_id}: {e}")
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Modify configuration values via command line.')
    parser.add_argument('--site_start_date', metavar='s', nargs='+',
                        help='the site name and desired start date to begin polling from')
    args = parser.parse_args()

    config = load_config_from_file()

    if args.site_start_date:
        for index in range(len(args.site_start_date)):
            arg = args.site_start_date[index]
            if arg in config['sites']:  # if we see a name that matches a site Name
                try:
                    new_time = datetime.strptime(args.site_start_date[index+1], "%Y-%m-%d %H:%M:%S")
                    config['sites'][arg]['start_date'] = new_time
                    logging.info(f"Updated the start_date for {arg} to {new_time}")
                except ValueError as e:
                    logging.error(f"Failed to update start_date for {arg}: {e}")
    stix_taxii = StixTaxii(config)
    stix_taxii.collect_and_send_reports()
