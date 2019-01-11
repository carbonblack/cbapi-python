from cbapi.connection import BaseAPI
import logging

log = logging.getLogger(__name__)


class FeedModel(object):
    def __init__(self, cb):
        super(FeedModel, self).__init__()
        self._cb = cb

    def __str__(self):
        lines = []
        lines.append("{0:s} object, bound to {1:s}.".format(self.__class__.__name__, self._cb.session.server))

        for key, value in self.__dict__.items():
            status = "   "
            # TODO(ww): Don't special-case FeedModel?
            if isinstance(value, FeedModel):
                val = value.__class__.__name__
            else:
                val = str(value)
            if len(val) > 50:
                val = val[:47] + u"..."
            lines.append(u"{0:s} {1:>20s}: {2:s}".format(status, key, val))

        return "\n".join(lines)


class FeedInfo(FeedModel):
    """docstring for FeedInfo"""
    def __init__(self, cb, *, name, owner, provider_url, summary, category, access, id=None):
        super(FeedInfo, self).__init__(cb)
        self.name = name
        self.owner = owner
        self.provider_url = provider_url
        self.summary = summary
        self.summary = summary
        self.category = category
        self.access = access
        self.id = id

    def update(self, feedinfo):
        pass

    def delete(self):
        self._cb.delete_object("/threathunter/feedmgr/v1/feed/{}".format(self.id))

    def reports(self):
        resp = self._cb.get_object("/threathunter/feedmgr/v1/feed/{}/report".format(self.id))
        return [Report(self._cb, **report) for report in resp.get("results", [])]

    def replace(self, reports):
        pass


class QueryIOC(FeedModel):
    """docstring for QueryIOC"""
    def __init__(self, cb, *, search_query, index_type=None):
        super(QueryIOC, self).__init__(cb)
        self.search_query = search_query
        self.index_type = index_type


class Report(FeedModel):
    """docstring for Report"""
    def __init__(self, cb, *, id, timestamp, title, description, severity, link=None, tags=[], iocs=[], iocs_v2=[], visibility=None):
        super(Report, self).__init__(cb)
        self.id = id
        self.timestamp = timestamp
        self.title = title
        self.description = description
        self.severity = severity
        self.link = link
        self.tags = tags
        self.iocs = iocs
        self.iocs_v2 = iocs_v2
        self.visibility = visibility

    def delete(self):
        # TODO(ww): Pass feed_id in somehow.
        pass


class Feed(FeedModel):
    def __init__(self, cb, *, feedinfo, reports):
        super(Feed, self).__init__(cb)
        self.feedinfo = FeedInfo(self._cb, **feedinfo)
        self.reports = [Report(self._cb, **report) for report in reports]

    def delete(self):
        self.feedinfo.delete()

# class IOCs(object):
#     """docstring for IOCs"""
#     def __init__(self, arg):
#         super(IOCs, self).__init__()
#         self.arg = arg


class CbThreatHunterFeedAPI(BaseAPI):
    """The main entry point into the Cb ThreatHunter PSC Feed API.

    :param str profile: (optional) Use the credentials in the named profile when connecting to the Carbon Black server.
        Uses the profile named 'default' when not specified.

    Usage::

    >>> from cbapi.psc.threathunter import CbThreatHunterFeedAPI
    >>> cb = CbThreatHunterFeedAPI(profile="production")
    """
    def __init__(self, *args, **kwargs):
        super(CbThreatHunterFeedAPI, self).__init__(product_name="psc", *args, **kwargs)
        self._lr_scheduler = None

    def feeds(self, include_public=False):
        resp = self.get_object("/threathunter/feedmgr/v1/feed", query_parameters={"include_public": include_public})
        return [FeedInfo(self, **feed) for feed in resp.get("results", [])]

    def feed(self, feed_id):
        resp = self.get_object("/threathunter/feedmgr/v1/feed/{}".format(feed_id))
        return resp

    def create(self, feed):
        pass

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger("cbapi").setLevel(logging.DEBUG)
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    cb = CbThreatHunterFeedAPI()

    feeds = cb.feeds(include_public=True)

    for feed in feeds:
        print(feed)
