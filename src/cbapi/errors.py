#!/usr/bin/env python
"""Exceptions that are thrown by CBAPI operations."""

from cbapi.six import python_2_unicode_compatible


class ApiError(Exception):
    """Base class for all CBAPI errors; also raised for generic internal errors."""

    def __init__(self, message=None, original_exception=None):
        """
        Initialize the ApiError.

        Args:
            message (str): The actual error message.
            original_exception (Exception): The exception that caused this one to be raised.
        """
        self.original_exception = original_exception
        self.message = str(message)

    def __str__(self):
        """
        Convert the exception to a string.

        Returns:
            str: String equivalent of the exception.
        """
        return self.message


@python_2_unicode_compatible
class ClientError(ApiError):
    """A ClientError is raised when an HTTP 4xx error code is returned from the Carbon Black server."""

    def __init__(self, error_code, message, result=None, original_exception=None):
        """
        Initialize the ClientError.

        Args:
            error_code (int): The error code that was received from the server.
            message (str): The actual error message.
            result (object): The result of the operation from the server.
            original_exception (Exception): The exception that caused this one to be raised.
        """
        super(ClientError, self).__init__(message=message, original_exception=original_exception)

        self.error_code = error_code
        self.result = result

    def __str__(self):
        """
        Convert the exception to a string.

        Returns:
            str: String equivalent of the exception.
        """
        msg = "Received error code {0:d} from API".format(self.error_code)
        if self.message:
            msg += ": {0:s}".format(self.message)
        else:
            msg += " (No further information provided)"

        if self.result:
            msg += ". {}".format(self.result)
        return msg


@python_2_unicode_compatible
class QuerySyntaxError(ApiError):
    """The request contains a query with malformed syntax."""

    def __init__(self, uri, message=None, original_exception=None):
        """
        Initialize the QuerySyntaxError.

        Args:
            uri (str): The URI of the action that failed.
            message (str): The error message.
            original_exception (Exception): The exception that caused this one to be raised.
        """
        super(QuerySyntaxError, self).__init__(message=message, original_exception=original_exception)
        self.uri = uri

    def __str__(self):
        """
        Convert the exception to a string.

        Returns:
            str: String equivalent of the exception.
        """
        msg = "Received query syntax error for {0:s}".format(self.uri)
        if self.message:
            msg += ": {0:s}".format(self.message)

        return msg


@python_2_unicode_compatible
class ServerError(ApiError):
    """A ServerError is raised when an HTTP 5xx error code is returned from the Carbon Black server."""

    def __init__(self, error_code, message, result=None, original_exception=None):
        """
        Initialize the ServerError.

        Args:
            error_code (int): The error code that was received from the server.
            message (str): The actual error message.
            result (object): The result of the operation from the server.
            original_exception (Exception): The exception that caused this one to be raised.
        """
        super(ServerError, self).__init__(message=message, original_exception=original_exception)

        self.error_code = error_code
        self.result = result

    def __str__(self):
        """
        Convert the exception to a string.

        Returns:
            str: String equivalent of the exception.
        """
        msg = "Received error code {0:d} from API".format(self.error_code)
        if self.message:
            msg += ": {0:s}".format(self.message)
        else:
            msg += " (No further information provided)"

        if self.result:
            msg += ". {}".format(self.result)
        return msg


@python_2_unicode_compatible
class ObjectNotFoundError(ApiError):
    """The requested object could not be found in the Carbon Black datastore."""

    def __init__(self, uri, message=None, original_exception=None):
        """
        Initialize the ObjectNotFoundError.

        Args:
            uri (str): The URI of the action that failed.
            message (str): The error message.
            original_exception (Exception): The exception that caused this one to be raised.
        """
        super(ObjectNotFoundError, self).__init__(message=message, original_exception=original_exception)
        self.uri = uri

    def __str__(self):
        """
        Convert the exception to a string.

        Returns:
            str: String equivalent of the exception.
        """
        msg = "Received 404 (Object Not Found) for {0:s}".format(self.uri)
        if self.message:
            msg += ": {0:s}".format(self.message)

        return msg


@python_2_unicode_compatible
class TimeoutError(ApiError):
    """A requested operation timed out."""

    def __init__(self, uri=None, error_code=None, message=None, original_exception=None):
        """
        Initialize the TimeoutError.

        Args:
            uri (str): The URI of the action that timed out.
            error_code (int): The error code that was received from the server.
            message (str): The error message.
            original_exception (Exception): The exception that caused this one to be raised.
        """
        super(TimeoutError, self).__init__(message=message, original_exception=original_exception)
        self.uri = uri
        self.error_code = error_code

    def __str__(self):
        """
        Convert the exception to a string.

        Returns:
            str: String equivalent of the exception.
        """
        if self.uri:
            msg = "Timed out when requesting {0:s} from API".format(self.uri)
            if self.error_code:
                msg += " with HTTP status code {0:d}".format(self.error_code)
            if self.message:
                msg += ": {0:s}".format(self.message)
        else:
            msg = self.message

        return msg


@python_2_unicode_compatible
class UnauthorizedError(ApiError):
    """The action that was attempted was not authorized."""

    def __init__(self, uri, message=None, action="read", original_exception=None):
        """
        Initialize the UnauthorizedError.

        Args:
            uri (str): The URI of the action that was not authorized.
            message (str): The error message.
            action (str): The action that was being performed that was not authorized.
            original_exception (Exception): The exception that caused this one to be raised.
        """
        super(UnauthorizedError, self).__init__(message=message, original_exception=original_exception)
        self.uri = uri
        self.action = action

    def __str__(self):
        """
        Convert the exception to a string.

        Returns:
            str: String equivalent of the exception.
        """
        if self.message:
            return "Check your API Credentials: " + str(self.message)

        return "Unauthorized (Check API creds): attempted to {0:s} {1:s}".format(self.action, self.uri)


class ConnectionError(ApiError):
    """There was an error in the connection to the server."""

    pass


class CredentialError(ApiError):
    """The credentials had an unspecified error."""

    pass


class InvalidObjectError(ApiError):
    """An invalid object was received by the server."""

    pass


class InvalidHashError(Exception):
    """An invalid hash value was used."""

    pass


class MoreThanOneResultError(ApiError):
    """Only one object was requested, but multiple matches were found in the Carbon Black datastore."""

    pass
