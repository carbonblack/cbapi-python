from cbapi.psc.threathunter import CbThreatHunterAPI
from cbapi.psc.threathunter.models import Feed
import logging

log = logging.getLogger(__name__)

def get_feed_ids():
    cb = CbThreatHunterAPI()
    url = "/threathunter/feedmgr/v2/orgs/{}/feeds".format(cb.credentials.org_key)
    feeds = cb.get_object(url)
    if len(feeds['results']) == 0:
        print("No feeds are available for the org key {}".format(cb.credentials.org_key))
    else:
        for feed in feeds['results']:
            print("Feed name: {:<20} \t Feed ID: {:>20}".format(feed['name'], feed['id']))
if __name__ == '__main__':
    get_feed_ids()
