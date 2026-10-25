from datetime import datetime

from mongoengine import DateTimeField, Document, StringField

# Seconds an expired document is kept before MongoDB deletes it. During
# this period the expand command reports the url as expired; afterwards
# the shortened url can be reused
EXPIRED_RETENTION_SECONDS = 24 * 60 * 60


class ShortenedUrl(Document):
    complete_url: str = StringField(required=True)
    shortened_url: str = StringField(required=True, unique=True)
    # Stored in UTC: the TTL index compares it with the UTC time
    expiration_time: datetime = DateTimeField(required=True)

    meta = {
        "indexes": [
            {"fields": ["complete_url", "-expiration_time"]},
            {
                "fields": ["expiration_time"],
                "expireAfterSeconds": EXPIRED_RETENTION_SECONDS,
            },
        ],
    }
