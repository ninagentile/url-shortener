import secrets
import string
from datetime import timedelta

from mongoengine import NotUniqueError

from url_shortener.database.entities import ShortenedUrl
from url_shortener.database.queries import ShortenedUrlQueries
from url_shortener.dtos import CreatedShortenedUrlDTO
from url_shortener.exceptions import (
    ShortenedUrlExpired,
    ShortenedUrlNotFound,
    ShortUrlGenerationFailed,
)
from url_shortener.time_utils import utc_now

# Default expiration time expressed in seconds
DEFAULT_EXPIRES_IN = 3600

SHORT_URL_DOMAIN = "https://myurlshortener.com"
# 62 symbols: a-z, A-Z, 0-9
ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
# Max number of codes generated before giving up, in case of collisions
MAX_ATTEMPTS = 5


class ShorteningUrlService:
    @classmethod
    def get_shortened_url(
        cls, complete_url: str, expires_in: int = DEFAULT_EXPIRES_IN
    ) -> str:
        """
        Returns the shortened url of a complete url. If a valid one already
        exists it is returned, otherwise a new one is created

        Parameters
        ----------
        complete_url
            Complete url
        expires_in
            Seconds before a new shortened url expires. It doesn't change
            the expiration of an existing one

        Returns
        -------
        shortened_url
            Shortened url
        """
        try:
            shortened_url_doc = ShortenedUrlQueries.get_shortened_url(
                complete_url=complete_url
            )
            if cls._is_expired(shortened_url_doc):
                raise ShortenedUrlNotFound()
            return shortened_url_doc.shortened_url
        except ShortenedUrlNotFound:
            return cls._create_and_save_shortened_url(
                complete_url=complete_url, expires_in=expires_in
            )

    @classmethod
    def _create_and_save_shortened_url(
        cls, complete_url: str, expires_in: int
    ) -> str:
        """
        Creates a new shortened url and saves it in DB, generating a new
        code if the previous one is already taken

        Parameters
        ----------
        complete_url
            Complete url
        expires_in
            Seconds before the shortened url expires

        Returns
        -------
        shortened_url
            The new shortened url

        Raises
        ------
        ShortUrlGenerationFailed
            If no free code is found after MAX_ATTEMPTS attempts
        """
        for _ in range(MAX_ATTEMPTS):
            shortened_url_dto = cls._create_shortened_url(
                complete_url=complete_url, expires_in=expires_in
            )
            try:
                ShortenedUrlQueries.save_shortened_url(
                    complete_url=complete_url,
                    shortened_url=shortened_url_dto.shortened_url,
                    expiration_time=shortened_url_dto.expiration_time,
                )
                return shortened_url_dto.shortened_url
            except NotUniqueError:
                continue
        raise ShortUrlGenerationFailed(
            "Could not generate a unique shortened url, please try again"
        )

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
        now = utc_now()
        if shortened_url_doc.expiration_time <= now:
            return True
        return False

    @classmethod
    def _create_shortened_url(
        cls, complete_url: str, expires_in: int
    ) -> CreatedShortenedUrlDTO:
        return CreatedShortenedUrlDTO(
            shortened_url=ShortenedUrlCreator.shortened_url(),
            expiration_time=utc_now() + timedelta(seconds=expires_in),
        )


class ShortenedUrlCreator:
    @staticmethod
    def shortened_url() -> str:
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        return f"{SHORT_URL_DOMAIN}/{code}"
