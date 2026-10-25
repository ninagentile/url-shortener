from urllib.parse import urlparse

import mongoengine

from url_shortener.exceptions import InvalidCommand
from url_shortener.service import ShorteningUrlService


def connect():
    mongoengine.connect(
        host="mongodb://localhost:27017/",
        db="url_shortener",
    )


def validate_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise InvalidCommand(f"Invalid URL: {url}")


def validate_prefix(prefix):
    if prefix not in ["--minify", "--expand"]:
        raise InvalidCommand("Command is invalid, please try again")


def process_input(command: str) -> tuple[str, str]:
    command = command.strip()
    prefix, url = command.split("=", 1)
    validate_prefix(prefix)
    url = url.strip()
    validate_url(url=url)
    return prefix, url


if __name__ == "__main__":
    # connect to mongo DB
    connect()

    while True:
        command = input("Insert command: ")
        try:
            prefix, url = process_input(command)
            if "--minify=" in command:
                print(ShorteningUrlService.get_shortened_url(complete_url=url))
            elif "--expand=" in command:
                try:
                    print(ShorteningUrlService.expand_url(shortened_url=url))
                except Exception as e:
                    print(e)
            else:
                print("Invalid command, please try again")
        except InvalidCommand as e:
            print(e)
