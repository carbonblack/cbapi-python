#!/usr/bin/env python

from ..oldmodels import BaseModel, immutable, MutableModel
from ..models import MutableBaseModel, CreatableModelMixin, NewBaseModel
from contextlib import closing
from distutils.version import LooseVersion

from zipfile import ZipFile
import cbapi.six as six
if six.PY3:
    from io import BytesIO as StringIO
else:
    from cStringIO import StringIO


class EnforcementLevel:
    LevelHigh = 20
    LevelMedium = 30
    LevelLow = 40
    LevelNone = 80


class ApprovalRequest(MutableModel):
    urlobject = "/api/bit9platform/v1/approvalRequest"

    ResolutionNotResolved = 0
    ResolutionRejected = 1
    ResolutionApproved = 2
    ResolutionRuleChange = 3
    ResolutionInstaller = 4
    ResolutionUpdater = 5
    ResolutionPublisher = 6
    ResolutionOther = 7

    StatusSubmitted = 1
    StatusOpen = 2
    StatusClosed = 3

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(ApprovalRequest, self).__init__(cb, model_unique_id, initial_data)

    @property
    def fileCatalog(self):
        return self._join(FileCatalog, "fileCatalogId")

    @property
    def installerFileCatalog(self):
        return self._join(FileCatalog, "installerFileCatalogId")

    @property
    def processFileCatalog(self):
        return self._join(FileCatalog, "processFileCatalogId")

    @property
    def computer(self):
        return self._join(Computer, "computerId")


class Certificate(MutableModel):
    urlobject = "/api/bit9platform/v1/certificate"

    StateUnapproved = 1
    StateApproved = 2
    StateBanned = 3
    StateMixed = 4

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Certificate, self).__init__(cb, model_unique_id, initial_data)

    @property
    def parent(self):
        return self._join(Certificate, "parentCertificateId")

    @property
    def publisher(self):
        return self._join(Publisher, "publisherId")

    @property
    def firstSeenComputer(self):
        return self._join(Computer, "firstSeenComputerId")


class Computer(MutableBaseModel):
    urlobject = "/api/bit9platform/v1/computer"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Computer, self).__init__(cb, model_unique_id, initial_data)

    def _build_api_request_uri(self, http_method="GET"):
        base_uri = super(Computer, self)._build_api_request_uri(http_method=http_method)
        args = []

        if http_method == "PUT":
            if any(n in self._dirty_attributes
                   for n in ["debugLevel", "kernelDebugLevel", "debugFlags", "debugDuration", "ccLevel", "ccFlags"]):
                args.append("changeDiagnostics=true")
            if any(n in self._dirty_attributes
                   for n in ["template", "templateCloneCleanupMode", "templateCloneCleanupTime",
                             "templateCloneCleanupTimeScale", "templateTrackModsOnly"]):
                args.append("changeTemplate=true")
            if "tamperProtectionActive" in self._dirty_attributes:
                if self.get("tamperProtectionActive", True):
                    args.append("newTamperProtectionActive=true")
                else:
                    args.append("newTamperProtectionActive=false")

            if args:
                base_uri += "?{0}".format("&".join(args))

        return base_uri

    @property
    def policy(self):
        return self._join(Policy, "policyId")

    @policy.setter
    def policy(self, new_policy_id):
        self.policyId = new_policy_id

    @property
    def fileInstances(self):
        return self._cb.select(FileInstance).where("computerId:{0:d}".format(self.id))

    @property
    def templateComputer(self):
        return self._join(Computer, "templateComputerId")

    def resetCLIPassword(self):
        url = self._build_api_request_uri() + "?resetCLIPassword=true"
        self._cb.put_object(url, {})
        self.refresh()
        return getattr(self, "CLIPassword")


class Connector(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/bit9platform/v1/connector"
    swagger_meta_file = "protection/models/connector.yaml"

    @property
    def pendingAnalyses(self):
        return self._cb.select(PendingAnalysis).where("connectorId:{0:d}".format(self.id))


class DriftReport(NewBaseModel):
    urlobject = "/api/bit9platform/v1/driftReport"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


class DriftReportContents(NewBaseModel):
    urlobject = "/api/bit9platform/v1/driftReportContents"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


class Event(NewBaseModel):
    urlobject = "/api/bit9platform/v1/event"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Event, self).__init__(cb, model_unique_id, initial_data)

    @property
    def fileCatalog(self):
        return self._join(FileCatalog, "fileCatalogId")


class FileAnalysis(MutableModel):
    urlobject = "/api/bit9platform/v1/fileAnalysis"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(FileAnalysis, self).__init__(cb, model_unique_id, initial_data)


class FileCatalog(MutableBaseModel):
    urlobject = "/api/bit9platform/v1/fileCatalog"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(FileCatalog, self).__init__(cb, model_unique_id, initial_data)

    @property
    def computer(self):
        return self._cb.select(Computer, self.computerId)

    @property
    def publisher(self):
        return self._cb.select(Publisher, self.publisherId)

    @property
    def certificate(self):
        return self._cb.select(Certificate, self.certificateId)

    @property
    def fileHash(self):
        return getattr(self, "md5", None) or getattr(self, "sha1", None) or getattr(self, "sha256", None)


class FileInstance(MutableBaseModel):
    urlobject = "/api/bit9platform/v1/fileInstance"
    _change_object_http_method = "POST"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(FileInstance, self).__init__(cb, model_unique_id, initial_data)

    @property
    def computer(self):
        return self._join(Computer, "computerId")

    @property
    def fileCatalog(self):
        return self._join(FileCatalog, "fileCatalogId")


@immutable
class FileInstanceDeleted(BaseModel):
    urlobject = "/api/bit9platform/v1/fileInstanceDeleted"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(FileInstanceDeleted, self).__init__(cb, model_unique_id, initial_data)


@immutable
class FileInstanceGroup(BaseModel):
    urlobject = "/api/bit9platform/v1/fileInstanceGroup"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(FileInstanceGroup, self).__init__(cb, model_unique_id, initial_data)


class FileRule(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/bit9platform/v1/fileRule"
    swagger_meta_file = "protection/models/fileRule.yaml"

    StateUnapproved = 1
    StateApproved = 2
    StateBanned = 3

    SourceTypeManual = 1
    SourceTypeTrustedDirectory = 2
    SourceTypeReputation = 3
    SourceTypeImported = 4
    SourceTypeExternal = 5
    SourceTypeEventRule = 6
    SourceTypeApplicationTemplate = 7
    SourceTypeUnifiedManagement = 8

    PlatformWindows = 1
    PlatformMac = 2
    PlatformLinux = 4

    @property
    def fileCatalog(self):
        return self._join(FileCatalog, "fileCatalogId")

    @property
    def createdByUser(self):
        return self._join(User, "createdByUserId")


class FileUpload(MutableModel):
    urlobject = "/api/bit9platform/v1/fileUpload"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(FileUpload, self).__init__(cb, model_unique_id, initial_data)

    @property
    def file(self):
        with closing(self._cb.session.get(self._build_api_request_uri() + "?downloadFile=true", stream=True)) as r:
            z = StringIO(r.content)
            zf = ZipFile(z)
            fp = zf.open(zf.filelist[0], "r")
            return fp


class GrantedUserPolicyPermission(NewBaseModel):
    urlobject = "/api/bit9platform/v1/grantedUserPolicyPermission"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


@immutable
class InternalEvent(BaseModel):
    urlobject = "/api/bit9platform/v1/internalEvent"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(InternalEvent, self).__init__(cb, model_unique_id, initial_data)


@immutable
class MeteredExecution(BaseModel):
    urlobject = "/api/bit9platform/v1/meteredExecution"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(MeteredExecution, self).__init__(cb, model_unique_id, initial_data)


class Notification(MutableBaseModel, CreatableModelMixin):
    ResultNotAvailable = 0
    ResultClean = 1
    ResultPotentialThreat = 2
    ResultMalicious = 3

    urlobject = "/api/bit9platform/v1/notification"
    swagger_meta_file = "protection/models/notification.yaml"


@immutable
class Notifier(BaseModel):
    urlobject = "/api/bit9platform/v1/notifier"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Notifier, self).__init__(cb, model_unique_id, initial_data)


class PendingAnalysis(MutableModel):
    urlobject = "/api/bit9platform/v1/pendingAnalysis"

    StatusScheduled = 0
    StatusSubmitted = 1
    StatusProcessed = 2
    StatusAnalyzed = 3
    StatusError = 4
    StatusCancelled = 5

    ResultNotAvailable = 0
    ResultClean = 1
    ResultPotentialThreat = 2
    ResultMalicious = 3

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(PendingAnalysis, self).__init__(cb, model_unique_id, initial_data)

    @property
    def file(self):
        with closing(self._cb.session.get(self._build_api_request_uri() + "?downloadFile=true", stream=True)) as r:
            z = StringIO(r.content)
            zf = ZipFile(z)
            fp = zf.open(zf.filelist[0], "r")
            return fp

    def create_notification(self, **kwargs):
        n = self._cb.create(Notification, **kwargs)
        n.fileAnalysisId = self.id
        return n

    @property
    def fileCatalog(self):
        return self._cb.select(FileCatalog, self.fileCatalogId)

    @property
    def fileHash(self):
        return getattr(self, "md5", None) or getattr(self, "sha1", None) or getattr(self, "sha256", None)


class Policy(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/bit9platform/v1/policy"
    swagger_meta_file = "protection/models/policy.yaml"


class Publisher(MutableModel):
    urlobject = "/api/bit9platform/v1/publisher"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Publisher, self).__init__(cb, model_unique_id, initial_data)


class PublisherCertificate(NewBaseModel):
    urlobject = "/api/bit9platform/v1/publisherCertificate"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


class ScriptRule(MutableBaseModel):
    urlobject = "/api/bit9platform/v1/scriptRule"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


@immutable
class ServerConfig(BaseModel):
    urlobject = "/api/bit9platform/v1/serverConfig"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(ServerConfig, self).__init__(cb, model_unique_id, initial_data)


@immutable
class ServerPerformance(BaseModel):
    urlobject = "/api/bit9platform/v1/serverPerformance"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(ServerPerformance, self).__init__(cb, model_unique_id, initial_data)


class Updater(MutableModel):
    urlobject = "/api/bit9platform/v1/updater"

    def __init__(self, cb, model_unique_id, initial_data=None):
        super(Updater, self).__init__(cb, model_unique_id, initial_data)


class TrustedDirectory(MutableBaseModel):
    urlobject = "/api/bit9platform/v1/trustedDirectory"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


class TrustedUser(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/bit9platform/v1/trustedUser"
    swagger_meta_file = "protection/models/trustedUser.yaml"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


class User(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/bit9platform/v1/user"
    swagger_meta_file = "protection/models/user.yaml"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")


class UserGroup(MutableBaseModel, CreatableModelMixin):
    urlobject = "/api/bit9platform/v1/userGroup"
    swagger_meta_file = "protection/models/userGroup.yaml"

    @classmethod
    def _minimum_server_version(cls):
        return LooseVersion("8.0")
