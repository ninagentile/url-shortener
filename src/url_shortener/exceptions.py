class ShortenedUrlNotFound(Exception):
    """
    Exception raised when a shortened url cannot be found given a
    complete url
    """


class ShortenedUrlExpired(Exception):
    """
    Exception raised when a shortened url is expired
    """


class InvalidCommand(Exception):
    """
    Exception raised when a command is invalid
    """


class InvalidURL(Exception):
    """
    Exception raised when a URL is invalid
    """


class CompleteUrlNotFound(Exception):
    """
    Exception raised when a complete url cannot be found given a
    shortened url
    """


class ShortUrlGenerationFailed(Exception):
    """
    Exception raised when a unique shortened url cannot be generated
    """
