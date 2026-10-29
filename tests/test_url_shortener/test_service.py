from datetime import timedelta
from unittest import mock

import pytest

from url_shortener.database.entities import ShortenedUrl
from url_shortener.db_mocker import DbMocker
from url_shortener.dtos import CreatedShortenedUrlDTO
from url_shortener.exceptions import (
    CompleteUrlNotFound,
    ShortenedUrlExpired,
    ShortUrlGenerationFailed,
)
from url_shortener.service import (
    ALPHABET,
    CODE_LENGTH,
    DEFAULT_EXPIRES_IN,
    SHORT_URL_DOMAIN,
    ShortenedUrlCreator,
    ShorteningUrlService,
)
from url_shortener.time_utils import utc_now


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


class TestMinifyUrl:
    def test_no_url_saved_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = ShorteningUrlService.minify_url(
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

        shortened_url = ShorteningUrlService.minify_url(
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

        shortened_url = ShorteningUrlService.minify_url(
            complete_url=complete_url
        )
        assert isinstance(shortened_url, str)
        assert shortened_url != shortened_url_doc.shortened_url

    def test_multiple_shortened_urls_one_valid(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        for i in range(3):
            DbMocker.mock_shortened_url(
                is_expired=True,
                complete_url=complete_url,
                shortened_url=f"shortened_url_{i}",
            )
        shortened_url = "www.shorturl.com/1234"
        DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url=complete_url,
            shortened_url=shortened_url,
        )
        loaded_url = ShorteningUrlService.minify_url(
            complete_url=complete_url
        )
        assert loaded_url == shortened_url

    def test_multiple_shortened_urls_none_valid(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_urls = []
        for i in range(3):
            shortened_url = f"shortened_url_{i}"
            DbMocker.mock_shortened_url(
                is_expired=True,
                complete_url=complete_url,
                shortened_url=shortened_url,
            )
            shortened_urls.append(shortened_url)
        loaded_url = ShorteningUrlService.minify_url(
            complete_url=complete_url
        )
        # a new short URL is returned, since none is valid
        assert loaded_url not in shortened_urls


def test_is_expired():
    expired_date = utc_now() - timedelta(hours=1)
    non_expired_date = utc_now() + timedelta(hours=1)

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
            expires_in=DEFAULT_EXPIRES_IN,
        )
        assert isinstance(shortened_url_dto, CreatedShortenedUrlDTO)
        assert shortened_url_dto.shortened_url != complete_url
        assert shortened_url_dto.expiration_time >= utc_now()
        elapsed_seconds = (
            shortened_url_dto.expiration_time - utc_now()
        ).total_seconds()
        assert 0 < elapsed_seconds <= DEFAULT_EXPIRES_IN


class TestExpiresIn:
    def test_default_expires_in(self):
        ShorteningUrlService.minify_url(
            complete_url="https://www.a.com/"
        )
        doc = ShortenedUrl.objects.get(complete_url="https://www.a.com/")
        seconds_left = (doc.expiration_time - utc_now()).total_seconds()
        assert DEFAULT_EXPIRES_IN - 5 < seconds_left <= DEFAULT_EXPIRES_IN

    def test_custom_expires_in(self):
        ShorteningUrlService.minify_url(
            complete_url="https://www.a.com/", expires_in=10
        )
        doc = ShortenedUrl.objects.get(complete_url="https://www.a.com/")
        seconds_left = (doc.expiration_time - utc_now()).total_seconds()
        assert 5 < seconds_left <= 10

    def test_expires_in_does_not_change_valid_short(self):
        """
        A valid shortened url is returned as it is, with its original
        expiration time
        """
        doc = DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url="https://www.a.com/",
            shortened_url=f"{SHORT_URL_DOMAIN}/valid00",
        )
        short_url = ShorteningUrlService.minify_url(
            complete_url="https://www.a.com/", expires_in=10
        )
        assert short_url == doc.shortened_url
        doc.reload()
        seconds_left = (doc.expiration_time - utc_now()).total_seconds()
        assert seconds_left > 10


class TestShortenedUrlCreator:
    def test_shortened_url(self):
        short_url = ShortenedUrlCreator.shortened_url()
        assert isinstance(short_url, str)

    def test_shortened_url_format(self):
        short_url = ShortenedUrlCreator.shortened_url()
        prefix, code = short_url.rsplit("/", 1)
        assert prefix == SHORT_URL_DOMAIN
        assert len(code) == CODE_LENGTH
        assert all(char in ALPHABET for char in code)


class TestCollisions:
    def test_retry_on_collision(self):
        DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url="https://www.a.com",
            shortened_url=f"{SHORT_URL_DOMAIN}/taken00",
        )
        # first generated code collides, second one is free
        with mock.patch.object(
            ShortenedUrlCreator,
            "shortened_url",
            side_effect=[
                f"{SHORT_URL_DOMAIN}/taken00",
                f"{SHORT_URL_DOMAIN}/free000",
            ],
        ):
            short_url = ShorteningUrlService.minify_url(
                complete_url="https://www.b.com"
            )
        assert short_url == f"{SHORT_URL_DOMAIN}/free000"

    def test_too_many_collisions(self):
        DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url="https://www.a.com",
            shortened_url=f"{SHORT_URL_DOMAIN}/taken00",
        )
        with (
            mock.patch.object(
                ShortenedUrlCreator,
                "shortened_url",
                return_value=f"{SHORT_URL_DOMAIN}/taken00",
            ),
            pytest.raises(ShortUrlGenerationFailed),
        ):
            ShorteningUrlService.minify_url(
                complete_url="https://www.b.com"
            )


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
