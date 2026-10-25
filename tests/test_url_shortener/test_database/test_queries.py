from datetime import datetime, timedelta

import pytest

from url_shortener.database.entities import ShortenedUrl
from url_shortener.database.queries import ShortenedUrlQueries
from url_shortener.db_mocker import DbMocker
from url_shortener.exceptions import ShortenedUrlNotFound, CompleteUrlNotFound


class TestGetShortenedUrlQueries:
    def test_get_shortened_url_existing_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = "www.shorturl.com/1234"
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

    def test_get_shortened_url_not_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"

        with pytest.raises(ShortenedUrlNotFound):
            ShortenedUrlQueries.get_shortened_url(complete_url=complete_url)


class TestSaveShortenedUrlQueries:
    def test_save_shortened_url(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = "www.shorturl.com/1234"
        expiration_time = datetime.now() + timedelta(hours=1)
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
        shortened_url = "www.shorturl.com/1234"
        doc = DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )
        loaded_complete_url = ShortenedUrlQueries.get_by_shortened_url(
            shortened_url=shortened_url
        )
        assert isinstance(loaded_complete_url, str)
        assert loaded_complete_url == complete_url

    def test_get_complete_url_not_on_db(self):
        shortened_url = "www.shorturl.com/1234"

        with pytest.raises(CompleteUrlNotFound):
            ShortenedUrlQueries.get_by_shortened_url(
                shortened_url=shortened_url
            )
