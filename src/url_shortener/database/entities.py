import datetime

from mongoengine import Document, StringField, DateTimeField


class ShortenedUrl(Document):
    complete_url: str = StringField(required=True)
    shortened_url: str = StringField(required=True, unique=True)
    expiration_time: datetime = DateTimeField(required=True)
