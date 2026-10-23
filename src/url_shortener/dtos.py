from datetime import datetime
from pydantic import BaseModel


class CreatedShortenedUrlDTO(BaseModel):
    shortened_url: str
    expiration_time: datetime
