from datetime import datetime, timedelta

from url_shortener.database.entities import ShortenedUrl
from url_shortener.time_utils import utc_now


class DbMocker:
    @classmethod
    def mock_shortened_url(
        cls, is_expired: bool, shortened_url: str, complete_url: str
    ) -> ShortenedUrl:
        if is_expired:
            expiration_time = utc_now() - timedelta(hours=1)
        else:
            expiration_time = utc_now() + timedelta(hours=1)
        return ShortenedUrl(
            complete_url=complete_url,
            shortened_url=shortened_url,
            expiration_time=expiration_time,
        ).save()

    @classmethod
    def mock_shortened_url_with_expiration(
        cls, expiration_time: datetime, shortened_url: str, complete_url: str
    ) -> ShortenedUrl:
        return ShortenedUrl(
            complete_url=complete_url,
            shortened_url=shortened_url,
            expiration_time=expiration_time,
        ).save()
