from urllib.parse import urlparse

import mongoengine

from url_shortener.exceptions import InvalidCommand, InvalidURL
from url_shortener.service import ShorteningUrlService
from url_shortener.validation import (
    process_input,
)


def connect():
    mongoengine.connect(
        host="mongodb://localhost:27017/",
        db="url_shortener",
    )


if __name__ == "__main__":
    # connect to mongo DB
    connect()

    while True:
        command = input("Insert command: ")
        try:
            prefix, url = process_input(command)
            if prefix == "--minify":
                print(ShorteningUrlService.get_shortened_url(complete_url=url))
            elif prefix == "--expand":
                try:
                    print(ShorteningUrlService.expand_url(shortened_url=url))
                except Exception as e:
                    print(e)
            else:
                print("Invalid command, please try again")
        except (InvalidCommand, InvalidURL) as e:
            print(e)
