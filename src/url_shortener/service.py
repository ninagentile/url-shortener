import secrets
import string
from datetime import datetime, timedelta

from mongoengine import NotUniqueError

from url_shortener.database.entities import ShortenedUrl
from url_shortener.database.queries import ShortenedUrlQueries
from url_shortener.dtos import CreatedShortenedUrlDTO
from url_shortener.exceptions import (
    ShortenedUrlNotFound,
    ShortenedUrlExpired,
    ShortUrlGenerationFailed,
)

# Expiration time expressed in seconds
EXPIRES_IN = 30

SHORT_URL_DOMAIN = "https://myurlshortener.com"
# 62 symbols: a-z, A-Z, 0-9
ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
# Max number of codes generated before giving up, in case of collisions
MAX_ATTEMPTS = 5


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
            return cls._create_and_save_shortened_url(
                complete_url=complete_url
            )

    @classmethod
    def _create_and_save_shortened_url(cls, complete_url: str) -> str:
        """
        Creates a new shortened url and saves it in DB, generating a new
        code if the previous one is already taken

        Parameters
        ----------
        complete_url
            Complete url

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
                complete_url=complete_url
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
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        return f"{SHORT_URL_DOMAIN}/{code}"
