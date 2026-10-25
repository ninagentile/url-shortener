from datetime import datetime, timedelta

import pytest

from url_shortener.database.entities import ShortenedUrl
from url_shortener.dtos import CreatedShortenedUrlDTO
from url_shortener.exceptions import CompleteUrlNotFound, ShortenedUrlExpired
from url_shortener.service import (
    ShorteningUrlService,
    ShortenedUrlCreator,
    EXPIRES_IN,
)
from url_shortener.db_mocker import DbMocker


@pytest.fixture
def valid_shortened_url_doc() -> ShortenedUrl:
    complete_url = "www.python.org/some_resource/1234&a=1"
    shortened_url = "www.shorturl.com/1234"
    return DbMocker.mock_shortened_url(
        is_expired=False,
        complete_url=complete_url,
        shortened_url=shortened_url,
    )


@pytest.fixture
def invalid_shortened_url_doc() -> ShortenedUrl:
    complete_url = "www.python.org/some_resource/1234&a=1"
    shortened_url = "www.shorturl.com/1234"
    return DbMocker.mock_shortened_url(
        is_expired=True,
        complete_url=complete_url,
        shortened_url=shortened_url,
    )


class TestGetShortenedUrl:
    def test_no_url_saved_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = ShorteningUrlService.get_shortened_url(
            complete_url=complete_url
        )
        assert isinstance(shortened_url, str)

        # check the URL is saved on DB
        saved_doc = ShortenedUrl.objects.get(complete_url=complete_url)
        assert saved_doc.complete_url == complete_url
        assert saved_doc.shortened_url == shortened_url

    def test_url_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = "www.shorturl.com/1234"
        shortened_url_doc = DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )

        shortened_url = ShorteningUrlService.get_shortened_url(
            complete_url=complete_url
        )
        assert isinstance(shortened_url, str)
        assert shortened_url == shortened_url_doc.shortened_url

    def test_expired_url_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = "www.shorturl.com/1234"
        shortened_url_doc = DbMocker.mock_shortened_url(
            is_expired=True,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )

        shortened_url = ShorteningUrlService.get_shortened_url(
            complete_url=complete_url
        )
        assert isinstance(shortened_url, str)
        assert shortened_url != shortened_url_doc.shortened_url


def test_is_expired():
    expired_date = datetime.now() - timedelta(hours=1)
    non_expired_date = datetime.now() + timedelta(hours=1)

    assert ShorteningUrlService._is_expired(
        ShortenedUrl(expiration_time=expired_date)
    )
    assert not ShorteningUrlService._is_expired(
        ShortenedUrl(expiration_time=non_expired_date)
    )


class TestCreateShortenedUrl:
    def test_create_shortened_url(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url_dto = ShorteningUrlService._create_shortened_url(
            complete_url=complete_url,
        )
        assert isinstance(shortened_url_dto, CreatedShortenedUrlDTO)
        assert shortened_url_dto.shortened_url != complete_url
        assert shortened_url_dto.expiration_time >= datetime.now()
        assert (
            EXPIRES_IN
            == (shortened_url_dto.expiration_time - datetime.now()).seconds
        )


class TestShortenedUrlCreator:
    def test_shortened_url(self):
        short_url = ShortenedUrlCreator.shortened_url()
        assert isinstance(short_url, str)

    def test_all_different_shortened_urls(self):
        size = 100000
        short_urls = {ShortenedUrlCreator.shortened_url() for _ in range(size)}
        # Check no duplicated URLs are created
        assert len(short_urls) == size


class TestExpandUrl:
    def test_expand_url_existing(self, valid_shortened_url_doc):
        expanded_url = ShorteningUrlService.expand_url(
            shortened_url=valid_shortened_url_doc.shortened_url
        )
        assert isinstance(expanded_url, str)
        assert expanded_url == valid_shortened_url_doc.complete_url

    def test_expand_url_expired(self, invalid_shortened_url_doc):
        with pytest.raises(ShortenedUrlExpired):
            ShorteningUrlService.expand_url(
                shortened_url=invalid_shortened_url_doc.shortened_url
            )

    def test_expand_url_not_found(self):
        with pytest.raises(CompleteUrlNotFound):
            ShorteningUrlService.expand_url(shortened_url="Some URL")
