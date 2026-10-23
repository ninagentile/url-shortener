from datetime import datetime

from url_shortener.database.entities import ShortenedUrl
from url_shortener.database.queries import ShortenedUrlQueries
from url_shortener.exceptions import ShortenedUrlNotFound


class ShortenedUrlService:
    @classmethod
    def shorten_url(cls, complete_url: str) -> str:
        try:
            shorten_url_doc = ShortenedUrlQueries.get_shortened_url(
                complete_url=complete_url
            )
            if cls._is_expired(shorten_url_doc):
                raise ShortenedUrlNotFound()
            return shorten_url_doc.shortened_url
        except ShortenedUrlNotFound:
            # Create the shortened URL and save it in DB
            shorten_url = cls._create_shorten_url
            yield shorten_url
            ShortenedUrlQueries.save_shortened_url(
                complete_url=complete_url,
                shorten_url=shorten_url,
                expiration_date=expiration_date
            )

    @classmethod
    def _is_expired(cls, shorten_url_doc: ShortenedUrl) -> bool:
        """
        Returns True if the shortened url is expired

        Parameters
        ----------
        shorten_url_doc
            ShortenedUrl document

        Returns
        -------
        is_expired
            True if the shortened url is expired
        """
        now = datetime.now()
        if shorten_url_doc.expiration_time > now:
            return True
        return False