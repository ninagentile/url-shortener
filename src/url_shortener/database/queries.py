from datetime import datetime

from mongoengine import DoesNotExist

from url_shortener.database.entities import ShortenedUrl
from url_shortener.exceptions import ShortenedUrlNotFound, CompleteUrlNotFound


class ShortenedUrlQueries:
    """
    Query class to retrieve and save shortened urls
    """

    @staticmethod
    def get_shortened_url(complete_url: str) -> ShortenedUrl:
        """
        Returns a shortened url based on a complete url

        Parameters
        ----------
        complete_url
            Complete url

        Returns
        -------
        shortened_url
            Shortened url version of the complete url, if any

        Raises
        ------
        ShortenedUrlNotFound
            If the shortened url cannot be found
        """
        # Handle case of url that is minimized multiple times after its
        # expiration
        minimized_urls = ShortenedUrl.objects.filter(
            complete_url=complete_url
        ).order_by("-expiration_time")
        if len(minimized_urls) > 0:
            return minimized_urls[0]
        else:
            raise ShortenedUrlNotFound(
                f"No shortened url found for complete URL: {complete_url}"
            )

    @classmethod
    def save_shortened_url(
        cls, complete_url: str, shortened_url: str, expiration_time: datetime
    ):
        ShortenedUrl(
            complete_url=complete_url,
            shortened_url=shortened_url,
            expiration_time=expiration_time,
        ).save()

    @classmethod
    def get_by_shortened_url(cls, shortened_url: str) -> ShortenedUrl:
        try:
            return ShortenedUrl.objects.get(shortened_url=shortened_url)
        except DoesNotExist:
            raise CompleteUrlNotFound(
                f"No complete url found for short URL: {shortened_url}"
            )
