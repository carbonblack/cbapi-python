from cbapi.connection import BaseAPI
from cbapi.errors import ApiError
from six import string_types
import logging
import functools
import validators
import time

log = logging.getLogger(__name__)


class CbTHFeedError(ApiError):
    """Represents a general error while interacting
    with the ThreatHunter Feed API.
    """
    pass


class FeedValidationError(CbTHFeedError):
    """Represents a failure when validating the fields
    of a Feed API model.
    """
    pass


# TODO(ww): Integrate this with cbapi.NewBaseModel maybe?
# Is there enough similarity between the two?
class FeedBaseModel(object):
    _safe_dict_types = (str, int, float, bool, type(None),)

    def __str__(self):
        lines = []
        lines.append("{0:s} object, bound to {1:s}.".format(self.__class__.__name__, self._cb.session.server))

        for key, value in self.__dict__.items():
            status = "   "
            # TODO(ww): Don't special-case FeedBaseModel?
            if isinstance(value, FeedBaseModel):
                val = value.__class__.__name__
            else:
                val = str(value)
            if len(val) > 50:
                val = val[:47] + u"..."
            lines.append(u"{0:s} {1:>20s}: {2:s}".format(status, key, val))

        return "\n".join(lines)

    def _as_dict(self):
        blob = {}
        for key, value in self.__dict__.items():
            if isinstance(value, self._safe_dict_types):
                blob[key] = value
            elif isinstance(value, list):
                if all(isinstance(x, FeedBaseModel) for x in value):
                    blob[key] = [x._as_dict() for x in value]
                elif all(isinstance(x, self._safe_dict_types) for x in value):
                    blob[key] = value
                else:
                    raise CbTHFeedError("unsupported type for attribute {}: {}".format(key, value.__class__.__name__))
            elif isinstance(value, FeedBaseModel):
                blob[key] = value._as_dict()
            elif isinstance(value, CbThreatHunterFeedAPI):
                continue
            else:
                raise CbTHFeedError("unsupported type for attribute {}: {}".format(key, value.__class__.__name__))
        return blob


class APIAwareModel(FeedBaseModel):
    def __init__(self, cb):
        super(APIAwareModel, self).__init__()
        self._cb = cb


class ValidatableModel(FeedBaseModel):
    @classmethod
    def _ensure_valid(cls, func):
        @functools.wraps(func)
        def wrap_ensure_valid(self, *args, **kwargs):
            self._validate()
            return func(self, *args, **kwargs)
        return wrap_ensure_valid

    def _validate(self):
        # If a subclass gives us a basic validation schema, use it.
        if self._validation_schema:
            for attr, exp_type in self._validation_schema.items():
                value = self.__dict__[attr]
                if not value or not isinstance(value, exp_type):
                    raise FeedValidationError(
                        "expected truthy {}={}, got '{}'".format(attr,
                                                                 exp_type.__name__,
                                                                 value))
        else:
            raise CbTHFeedError("_validate() not implemented")


class FeedInfo(APIAwareModel, ValidatableModel):
    """Represents the metadata associated with a :py:class:`Feed` either
    retrieved from the Feed API or ready to be sent to the Feed API.
    """
    _validation_schema = {
        'name': str,
        'owner': str,
        'provider_url': str,
        'summary': str,
        'category': str,
        'access': str,
    }

    def __init__(self, cb, *, name, owner, provider_url, summary, category, access, id=None):
        """Creates a new FeedInfo.
        """
        super(FeedInfo, self).__init__(cb)
        self.name = name
        self.owner = owner
        self.provider_url = provider_url
        self.summary = summary
        self.summary = summary
        self.category = category
        self.access = access
        self.id = id

    def _validate(self):
        super(FeedInfo, self)._validate()

        if not validators.url(self.provider_url):
            raise FeedValidationError("provider_url must be a URL")
        if self.access not in ['public', 'private']:
            raise FeedValidationError("access must be either 'public' or 'private'")

    def create_report(self, **kwargs):
        timestamp = kwargs.pop("timestamp", int(time.time()))
        return Report(self._cb, timestamp=timestamp, **kwargs)

    @ValidatableModel._ensure_valid
    def update(self, **kwargs):
        """Updates this FeedInfo instance with new fields on the Feed API server.

        :param kwargs: (optional) The fields to change within this instance
        :return: A new :py:class:`FeedInfo` with the updated fields
        :rtype: :py:class:`FeedInfo`
        :raise FeedValidationError: if this FeedInfo doesn't have an ID
        """
        # NOTE(ww): We allow FeedInfos to be instantiated without an ID for
        # server side creation, so normal validation can't handle this case.
        if not self.id:
            raise FeedValidationError("update() called without feed ID")

        attrs = {**self._as_dict(), **kwargs}
        new_info = FeedInfo(self._cb, **attrs)

        resp = self._cb.put_object("/feedmgr/v1/feed/{}/feedinfo".format(self.id), new_info._as_dict())
        return FeedInfo(self._cb, **resp.json())

    def delete(self):
        """Deletes the feed associated with this FeedInfo from
        the Feed API server.
        """
        if not self.id:
            raise FeedValidationError("delete() called without feed ID")
        self._cb.delete_feed(self)

    def reports(self):
        """Retrieves the reports associated with this FeedInfo
        from the Feed API server.
        """
        if not self.id:
            raise FeedValidationError("reports() called without feed ID")

        resp = self._cb.get_object("/threathunter/feedmgr/v1/feed/{}/report".format(self.id))
        return [Report(self._cb, **report) for report in resp.get("results", [])]

    def replace(self, reports):
        """Replaces the reports currently associated with this FeedInfo
        with the given reports.

        :param reports: the replacement reports
        :type reports: list of :py:class:`Report`
        :return: Whether or not the replacement succeeded
        :rtype: bool
        """
        # [report._validate() for report in reports]
        body = {"reports": [report._as_dict() for report in reports]}
        resp = self._cb.post_object("/feedmgr/v1/feed/{}/report".format(self.id), body)
        return resp.json().get("success", False)


# TODO(ww): Do we need this?
class QueryIOC(FeedBaseModel):
    def __init__(self, *, search_query, index_type=None):
        super(QueryIOC, self).__init__(cb)
        self.search_query = search_query
        self.index_type = index_type


class Report(ValidatableModel):
    """Represents a report either sendable to or retrieved from
    the Feed API server. Reports are uniquely identified within
    a feed and contain one or more :py:class:`IOC`s.
    """
    _validation_schema = {
        'id': str,
        'timestamp': int,
        'title': str,
        'description': str,
        'severity': int,
    }

    def __init__(self, *, id, timestamp, title, description, severity, link=None, tags=[], iocs=[], iocs_v2=[], visibility=None):
        # TODO(ww): Should we be supporting v1 as well? API docs
        # indicate that v1 will be automatically converted.
        if iocs:
            raise CbTHFeedError("expected iocs_v2 only")

        super(Report, self).__init__(cb)
        self.id = id
        self.timestamp = timestamp
        self.title = title
        self.description = description
        self.severity = severity
        self.link = link
        self.tags = tags
        self.iocs = []
        self.iocs_v2 = [IOC(**ioc) for ioc in iocs_v2]
        self.visibility = visibility

    def _validate(self):
        super(Report, self)._validate()

        # TODO(ww): Docs indicate that these lists are optional,
        # but are they *always* optional?
        for ioc in self.iocs:
            ioc._validate()
        for ioc_v2 in self.iocs_v2:
            ioc_v2._validate()


class Feed(APIAwareModel, ValidatableModel):
    """Represents a feed either retrieved from the Feed API or
    ready to be sent to the Feed API.
    """
    def __init__(self, cb, *, feedinfo, reports):
        """Creates a new report.

        :param feedinfo: The new feed's :py:class:`FeedInfo`
        :type feedinfo: :py:class:`FeedInfo`
        :param: reports: The new feed's list of :py:class:`Report`s
        :type reports: list of :py:class:`Report`
        """
        super(Feed, self).__init__(cb)
        self.feedinfo = FeedInfo(self._cb, **feedinfo)
        self.reports = [Report(**report) for report in reports]

    def _validate(self):
        self.feedinfo._validate()
        [report.validate() for report in self.reports]

    @ValidatableModel._ensure_valid
    def create(self):
        """Creates a feed on the Feed API server corresponding to this object's state.

        :return: A :py:class:`FeedInfo` instance containing the new feed's metadata
        :rtype: :py:class:`FeedInfo`
        """
        # Feeds that already have IDs have already been created.
        if self.feedinfo.id:
            raise CbTHFeedError("create() called on an already created feed")
        resp = self._cb.post_object("/threathunter/feedmgr/v1/feed", self._as_dict())
        return FeedInfo(self._cb, **resp.json())

    @ValidatableModel._ensure_valid
    def delete(self):
        """Deletes this feed from the Feed API server.
        """
        self._cb.delete_feed(self)

    def reports(self):
        """A wrapper for :py:meth:`FeedInfo.reports()`.
        """
        return self.feedinfo.reports()

    def replace(self, reports):
        """A wrapper for :py:meth:`FeedInfo.replace()`.
        """
        return self.feedinfo.replace(reports)

    @ValidatableModel._ensure_valid
    def delete_report(self, report):
        """Deletes the given report from the :py:class:`Feed`.

        :param report: The report to delete
        :type report: :py:class:`Report`
        """
        if report not in self.reports:
            raise CbTHFeedError("delete_report() called with a non-member report")

        # TODO(ww): Also delete the report from the local copy of the feed?
        self._cb.delete_object("/threathunter/feedmgr/v1/feed/{}/report/{}".format(self.feedinfo.id, report.id))


class IOC(ValidatableModel):
    """Represents one or more values of a particular IOC type.
    Encapsulated by :py:class:`Report` instances.
    """
    _validation_schema = {
        'id': str,
        'match_type': str,
        'values': list,
    }

    def __init__(self, *, id, match_type, values, field=None, link=None):
        """Creates a new IOC.
        """
        super(IOC, self).__init__(cb)
        self.id = id
        self.match_type = match_type
        self.values = values
        self.field = field
        self.link = link

    def _validate(self):
        super(IOC, self)._validate()

        if not all(value and isinstance(value, str) for value in self.values):
            raise FeedValidationError("expected iocs to be list(str)")

        # NOTE(ww): We only validate the field for non-query match types
        if self.match_type == "query":
            return

        if self.field not in ["netconn_domain"]:
            raise FeedValidationError("unknown IOC type: {}".format(self.field))

        if self.field == "netconn_domain":
            if not all(validators.domain(domain) for domain in self.values):
                raise FeedValidationError("one or more invalid domains")
        elif self.field == "something_else":
            pass


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
        """Gets all feeds known to the CbTH Feeds API.

        :param bool include_public: (optional) Whether to include public community feeds.
        :return: a list of :py:class:`Feed`s.
        """
        resp = self.get_object("/threathunter/feedmgr/v1/feed", query_parameters={"include_public": include_public})
        return [FeedInfo(self, **feed) for feed in resp.get("results", [])]

    def feed(self, feed_id):
        """Gets a :py:class:`Feed` by ID.

        :param str feed_id: The ID of the feed to retrieve
        :return: a new :py:class:`Feed` corresponding to the ID
        """
        resp = self.get_object("/threathunter/feedmgr/v1/feed/{}".format(feed_id))
        return resp

    def create_feed(self, reports=[], **kwargs):
        """A convenience method for :py:meth:`Feed.create()`.

        :param list(str) reports: (optional) Create the feed with the given :py:class:`Report`s
        :return: a new :py:class:`FeedInfo` corresponding to the new feed
        :rtype: FeedInfo

        Usage::

            >>> cb.create_feed(name="My Feed", owner="Nemo", provider_url="https://example.com", summary="Description", category="Partner", access="private")
        """
        feed = Feed(self, feedinfo=kwargs, reports=reports)
        return feed.create()

    def delete_feed(self, feed):
        """Deletes the given `feed`.

        :param feed: The feed to delete
        :type feed: :py:class:`Feed` or :py:class:`FeedInfo` or str
        :return: None
        :raises: :py:class:`CbTHFeedError` if `feed`'s type is unknown
        :raises: :py:class:`FeedValidationError` if `feed` is missing a feed ID
        """
        if isinstance(feed, Feed):
            feed_id = feed.feedinfo.id
        elif isinstance(feed, FeedInfo):
            feed_id = feed.id
        elif isinstance(feed, string_types):
            feed_id = feed
        else:
            raise CbTHFeedError("bad type for feed deletion: {}".format(feed.__class__.__name__))

        # NOTE(ww): Any of the options above might be partially initialized,
        # so we perform a sanity check here.
        if not feed_id:
            raise FeedValidationError("expected object with a valid feed ID")

        self.delete_object("/threathunter/feedmgr/v1/feed/{}".format(feed_id))


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger("cbapi").setLevel(logging.DEBUG)
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    cb = CbThreatHunterFeedAPI()

    feed = cb.create_feed(name="ToB Test Feed", owner="Trail of Bits",
                          provider_url="https://www.trailofbits.com/",
                          summary="A test feed.", category="Partner",
                          access="private")

    print(feed)

    feed = feed.update(summary="Changed description")

    print(feed)

    cb.delete_feed(feed)

    # ioc = {
    #     "id": "bazquux",
    #     "match_type": "equality",
    #     "values": ["example.com"],
    #     "field": "netconn_domain",
    # }

    # report = feed.create_report(id="foobar", title="Test Report",
    #                             description="Test Report Desc.",
    #                             severity=10, iocs_v2=[ioc])

    # feed.replace([report])

    # feeds = cb.feeds(include_public=False)
    # for feed in feeds:
    #     print(feed)
    #     feed.delete()

    # cb.delete_feed(feed)
