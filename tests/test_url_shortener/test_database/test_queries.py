from datetime import timedelta

import pytest

from url_shortener.database.entities import (
    EXPIRED_RETENTION_SECONDS,
    ShortenedUrl,
)
from url_shortener.database.queries import ShortenedUrlQueries
from url_shortener.db_mocker import DbMocker
from url_shortener.exceptions import CompleteUrlNotFound, ShortenedUrlNotFound
from url_shortener.time_utils import utc_now
from url_shortener.validation import SHORT_URL_DOMAIN


class TestGetShortenedUrlQueries:
    def test_get_shortened_url_existing_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = f"{SHORT_URL_DOMAIN}/1234"
        doc = DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )
        loaded_doc = ShortenedUrlQueries.get_shortened_url(
            complete_url=complete_url
        )
        assert isinstance(loaded_doc, ShortenedUrl)
        assert loaded_doc.complete_url == complete_url
        assert loaded_doc.shortened_url == shortened_url
        assert loaded_doc.id == doc.id

    def test_multiple_shortened_urls_one_valid(self):
        """
        Case of a complete url shortened multiple times, one valid and
        the others invalid. The valid is returned
        """
        complete_url = "www.python.org/some_resource/1234&a=1"
        for i in range(3):
            DbMocker.mock_shortened_url(
                is_expired=True,
                complete_url=complete_url,
                shortened_url=f"shortened_url_{i}",
            )
        shortened_url = f"{SHORT_URL_DOMAIN}/1234"
        doc = DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )
        loaded_doc = ShortenedUrlQueries.get_shortened_url(
            complete_url=complete_url
        )
        assert isinstance(loaded_doc, ShortenedUrl)
        assert loaded_doc.complete_url == complete_url
        assert loaded_doc.shortened_url == shortened_url
        assert loaded_doc.id == doc.id

    def test_multiple_shortened_urls_none_valid(self):
        """
        Case of a complete url shortened multiple times, but no valid.
        The newest is returned
        """
        complete_url = "www.python.org/some_resource/1234&a=1"
        # Expired, but within the retention period: older documents
        # would be deleted by the TTL index
        now = utc_now()

        newest_doc = DbMocker.mock_shortened_url_with_expiration(
            expiration_time=now - timedelta(hours=1),
            complete_url=complete_url,
            shortened_url="shortened_url_1",
        )
        DbMocker.mock_shortened_url_with_expiration(
            expiration_time=now - timedelta(hours=2),
            complete_url=complete_url,
            shortened_url="shortened_url_2",
        )

        loaded_doc = ShortenedUrlQueries.get_shortened_url(
            complete_url=complete_url
        )
        assert isinstance(loaded_doc, ShortenedUrl)
        assert loaded_doc.complete_url == complete_url
        assert loaded_doc.shortened_url == newest_doc.shortened_url
        assert loaded_doc.id == newest_doc.id

    def test_get_shortened_url_not_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"

        with pytest.raises(ShortenedUrlNotFound):
            ShortenedUrlQueries.get_shortened_url(complete_url=complete_url)


class TestSaveShortenedUrlQueries:
    def test_save_shortened_url(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = f"{SHORT_URL_DOMAIN}/1234"
        expiration_time = utc_now() + timedelta(hours=1)
        ShortenedUrlQueries.save_shortened_url(
            complete_url=complete_url,
            shortened_url=shortened_url,
            expiration_time=expiration_time,
        )

        loaded_doc = ShortenedUrl.objects.get(complete_url=complete_url)
        assert loaded_doc.expiration_time.replace(
            microsecond=0
        ) == expiration_time.replace(microsecond=0)
        assert loaded_doc.shortened_url == shortened_url


class TestGetCompleteUrlQueries:
    def test_get_complete_url_existing_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = f"{SHORT_URL_DOMAIN}/1234"
        doc = DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )
        loaded_complete_url = ShortenedUrlQueries.get_by_shortened_url(
            shortened_url=shortened_url
        )
        assert isinstance(loaded_complete_url, ShortenedUrl)
        assert loaded_complete_url.complete_url == doc.complete_url

    def test_get_complete_url_not_on_db(self):
        shortened_url = f"{SHORT_URL_DOMAIN}/1234"

        with pytest.raises(CompleteUrlNotFound):
            ShortenedUrlQueries.get_by_shortened_url(
                shortened_url=shortened_url
            )

    def test_get_complete_url_using_http_url(self):
        """
        Checks that shortened URLs work even if they start with http
        instead of https
        """
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = "https://myurlshortener.com/1234"
        DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )

        shortened_url_with_http = "http://myurlshortener.com/1234"
        assert (
            ShortenedUrlQueries.get_by_shortened_url(
                shortened_url=shortened_url_with_http,
            ).complete_url
            == complete_url
        )


class TestIndexes:
    def test_ttl_index_on_expiration_time(self):
        indexes = ShortenedUrl._get_collection().index_information()
        ttl_index = indexes["expiration_time_1"]
        assert ttl_index["key"] == [("expiration_time", 1)]
        assert ttl_index["expireAfterSeconds"] == EXPIRED_RETENTION_SECONDS

    def test_shortened_url_index_is_unique(self):
        indexes = ShortenedUrl._get_collection().index_information()
        assert indexes["shortened_url_1"]["unique"] is True
