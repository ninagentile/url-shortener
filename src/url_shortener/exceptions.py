class ShortenedUrlNotFound(Exception):
    """
    Exception raised when a shortened url cannot be found given a
    complete url
    """


class CompleteUrlNotFound(Exception):
    """
    Exception raised when a complete url cannot be found given a
    shortened url
    """
