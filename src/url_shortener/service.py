from datetime import datetime, timedelta

from bson import ObjectId

from url_shortener.database.entities import ShortenedUrl
from url_shortener.database.queries import ShortenedUrlQueries
from url_shortener.dtos import CreatedShortenedUrlDTO
from url_shortener.exceptions import (
    ShortenedUrlNotFound,
    ShortenedUrlExpired,
    CompleteUrlNotFound,
)

# Expiration time expressed in seconds
EXPIRES_IN = 3600


class ShorteningUrlService:
    @classmethod
    def get_shortened_url(cls, complete_url: str) -> str:
        # TODO: handle case of url already minimized
        try:
            shortened_url_doc = ShortenedUrlQueries.get_shortened_url(
                complete_url=complete_url
            )
            if cls._is_expired(shortened_url_doc):
                raise ShortenedUrlNotFound()
            return shortened_url_doc.shortened_url
        except ShortenedUrlNotFound:
            # Create the shortened URL and save it in DB
            shortened_url_dto = cls._create_shortened_url(
                complete_url=complete_url
            )
            ShortenedUrlQueries.save_shortened_url(
                complete_url=complete_url,
                shortened_url=shortened_url_dto.shortened_url,
                expiration_time=shortened_url_dto.expiration_time,
            )
            return shortened_url_dto.shortened_url

    @classmethod
    def expand_url(cls, shortened_url: str) -> str:
        doc = ShortenedUrlQueries.get_by_shortened_url(
            shortened_url=shortened_url
        )
        if cls._is_expired(doc):
            raise ShortenedUrlExpired(
                f"The shortened url {shortened_url} is expired"
            )
        return doc.complete_url

    @staticmethod
    def _is_expired(shortened_url_doc: ShortenedUrl) -> bool:
        """
        Returns True if the shortened url is expired

        Parameters
        ----------
        shortened_url_doc
            ShortenedUrl document

        Returns
        -------
        is_expired
            True if the shortened url is expired
        """
        now = datetime.now()
        if shortened_url_doc.expiration_time <= now:
            return True
        return False

    @classmethod
    def _create_shortened_url(
        cls, complete_url: str
    ) -> CreatedShortenedUrlDTO:
        return CreatedShortenedUrlDTO(
            shortened_url=ShortenedUrlCreator.shortened_url(),
            expiration_time=datetime.now() + timedelta(seconds=EXPIRES_IN),
        )


class ShortenedUrlCreator:
    @staticmethod
    def shortened_url() -> str:
        # TODO: find a better way to do it
        return f"shorturl.com/{ObjectId()}"
