from url_shortener.service import ShorteningUrlService
from url_shortener.database.entities import ShortenedUrl
from datetime import datetime, timedelta


class DbMocker:
    @classmethod
    def mock_shortened_url(
        cls, is_expired: bool, shortened_url: str, complete_url: str
    ) -> ShortenedUrl:
        if is_expired:
            expiration_time = datetime.now() - timedelta(hours=1)
        else:
            expiration_time = datetime.now() + timedelta(hours=1)
        return ShortenedUrl(
            complete_url=complete_url, shortened_url=shortened_url, expiration_time=expiration_time
        ).save()


class TestGetShortenedUrl:
    def test_no_url_saved_on_db(self):
        complete_url = "www.python.org/some_resource/1234&a=1"
        shortened_url = ShorteningUrlService.get_shortened_url(complete_url=complete_url)
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

        shortened_url = ShorteningUrlService.get_shortened_url(complete_url=complete_url)
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

        shortened_url = ShorteningUrlService.get_shortened_url(complete_url=complete_url)
        assert isinstance(shortened_url, str)
        assert shortened_url != shortened_url_doc.shortened_url
