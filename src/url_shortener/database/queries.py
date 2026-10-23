from mongoengine import DoesNotExist

from url_shortener.database.entities import ShortenedUrl
from url_shortener.exceptions import ShortenedUrlNotFound


class ShortenedUrlQueries:
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
        try:
            return ShortenedUrl.objects.get(complete_url=complete_url)
        except DoesNotExist:
            raise ShortenedUrlNotFound(
                f'No shortened url found for {complete_url}'
            )