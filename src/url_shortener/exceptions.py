class ShortenedUrlNotFound(Exception):
    """
    Exception raised when a shortened url cannot be found given a
    complete url
    """


class ShortenedUrlExpired(Exception):
    """
    Exception raised when a shortened url is expired
    """


class CompleteUrlNotFound(Exception):
    """
    Exception raised when a complete url cannot be found given a
    shortened url
    """
