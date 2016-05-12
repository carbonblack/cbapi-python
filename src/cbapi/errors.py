#!/usr/bin/env python


class ApiError(Exception):
    def __init__(self, message=None, original_exception=None):
        self.original_exception = original_exception
        self.message = message

    def __str__(self):
        return self.message


class ServerError(ApiError):
    """A ServerError is raised when an HTTP error code is returned from the Carbon Black server."""

    def __init__(self, error_code, message, result=None, original_exception=None):
        super(ServerError, self).__init__(message=message, original_exception=original_exception)

        self.error_code = error_code
        self.result = result

    def __str__(self):
        msg = "Received error code {0:d} from API".format(self.error_code)
        if self.message:
            msg += ": {0:s}".format(self.message)
        else:
            msg += " (No further information provided)"

        if self.result:
            msg += ". {}".format(self.result)
        return msg


class ObjectNotFoundError(ApiError):
    """The requested object could not be found in the Carbon Black datastore."""

    def __init__(self, uri, message=None, original_exception=None):
        super(ObjectNotFoundError, self).__init__(message=message, original_exception=original_exception)
        self.uri = uri

    def __str__(self):
        msg = "Received 404 (Object Not Found) for {0:s}".format(self.uri)
        if self.message:
            msg += ": {0:s}".format(self.message)

        return msg


class TimeoutError(ApiError):
    def __init__(self, uri, error_code=None, message=None, original_exception=None):
        super(TimeoutError, self).__init__(message=message, original_exception=original_exception)
        self.uri = uri
        self.error_code = error_code

    def __str__(self):
        msg = "Timed out when requesting {0:s} from API".format(self.uri)
        if self.error_code:
            msg += " with HTTP status code {0:d}".format(self.error_code)
        if self.message:
            msg += ": {0:s}".format(self.message)

        return msg


class UnauthorizedError(ApiError):
    def __init__(self, uri, message=None, action="read", original_exception=None):
        super(UnauthorizedError, self).__init__(message=message, original_exception=original_exception)
        self.uri = uri
        self.action = action

    def __str__(self):
        if self.message:
            return self.message

        return "Unauthorized: attempted to {0:s} {1:s}".format(self.action, self.uri)


class CredentialError(ApiError):
    pass


class InvalidObjectError(ApiError):
    pass


class InvalidHashError(Exception):
    pass


class MoreThanOneResultError(ApiError):
    """Only one object was requested, but multiple matches were found in the Carbon Black datastore."""
    pass

