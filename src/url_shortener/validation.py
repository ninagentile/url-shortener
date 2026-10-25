from urllib.parse import urlparse

from url_shortener.exceptions import InvalidCommand, InvalidURL
from url_shortener.service import SHORT_URL_DOMAIN


def validate_url(url: str, prefix: str):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise InvalidURL(f"Invalid URL: {url}")
    if (prefix == "--minify") and (
        parsed.hostname == urlparse(SHORT_URL_DOMAIN).hostname
    ):
        raise InvalidURL(f"Cannot shorten an already shortened URL: {url}")


def validate_prefix(prefix):
    if prefix not in ["--minify", "--expand"]:
        raise InvalidCommand(
            'Command should contain "--minify=" or "--expand=", please try again'
        )


def process_input(command: str) -> tuple[str, str]:
    command = command.strip()
    if "=" not in command:
        raise InvalidCommand("Invalid command, please try again")
    prefix, url = command.split("=", 1)
    validate_prefix(prefix)
    url = url.strip()
    validate_url(url=url, prefix=prefix)
    print(prefix, url)
    return prefix, url
