import argparse
import sys

import mongoengine

from url_shortener.exceptions import (
    CompleteUrlNotFound,
    InvalidCommand,
    InvalidURL,
    ShortenedUrlExpired,
    ShortUrlGenerationFailed,
)
from url_shortener.service import ShorteningUrlService
from url_shortener.validation import (
    normalize_url,
    process_input,
    validate_url,
)

# Errors with a message meant for the user
APP_ERRORS = (
    InvalidCommand,
    InvalidURL,
    CompleteUrlNotFound,
    ShortenedUrlExpired,
    ShortUrlGenerationFailed,
)


def connect():
    mongoengine.connect(
        host="mongodb://localhost:27017/",
        db="url_shortener",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="url-shortener",
        description=(
            "Shorten a URL or expand a shortened URL. "
            "Without arguments, starts an interactive session."
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--minify",
        metavar="URL",
        help="complete URL to shorten",
    )
    group.add_argument(
        "--expand",
        metavar="URL",
        help="shortened URL to expand",
    )
    return parser.parse_args(argv)


def run_command(prefix: str, url: str) -> str:
    """
    Runs a minify or expand command

    Parameters
    ----------
    prefix
        Either "--minify" or "--expand"
    url
        URL to minify or expand

    Returns
    -------
    result
        The shortened url for "--minify", the complete url for "--expand"
    """
    validate_url(url=url, prefix=prefix)
    url = normalize_url(url)
    if prefix == "--minify":
        return ShorteningUrlService.get_shortened_url(complete_url=url)
    return ShorteningUrlService.expand_url(shortened_url=url)


def interactive_session():
    while True:
        command = input("Insert command: ")
        try:
            prefix, url = process_input(command)
            print(run_command(prefix=prefix, url=url))
        except APP_ERRORS as e:
            print(e)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # connect to mongo DB
    connect()

    if args.minify is None and args.expand is None:
        interactive_session()
        return 0

    if args.minify is not None:
        prefix, url = "--minify", args.minify
    else:
        prefix, url = "--expand", args.expand
    try:
        print(run_command(prefix=prefix, url=url.strip()))
    except APP_ERRORS as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
