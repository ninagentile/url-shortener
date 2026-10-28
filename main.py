import argparse
import os
import sys

import mongoengine
from pymongo.errors import ConfigurationError, ConnectionFailure, PyMongoError

from url_shortener.exceptions import (
    CompleteUrlNotFound,
    InvalidCommand,
    InvalidURL,
    ShortenedUrlExpired,
    ShortUrlGenerationFailed,
)
from url_shortener.service import DEFAULT_EXPIRES_IN, ShorteningUrlService
from url_shortener.validation import (
    normalize_url,
    process_input,
    validate_url,
)

# Environment variable with the expiration time in seconds
EXPIRES_IN_ENV_VAR = "URL_SHORTENER_EXPIRES_IN"
# Max expiration time: 100 years, far from the max date MongoDB can store
MAX_EXPIRES_IN = 100 * 365 * 24 * 60 * 60

# Environment variable with the MongoDB connection string
MONGODB_URI_ENV_VAR = "MONGODB_URI"
DEFAULT_MONGODB_URI = "mongodb://localhost:27017/"
# Database used when the connection string doesn't contain one
DEFAULT_DB_NAME = "url_shortener"
# Milliseconds to wait for MongoDB before giving up
DB_TIMEOUT_MS = 3000
DB_NOT_REACHABLE_MESSAGE = (
    "Database not reachable: check that MongoDB is running and that "
    f"{MONGODB_URI_ENV_VAR} is correct"
)

# Options that take a URL, accepted only as "--option=URL"
URL_OPTIONS = ("--minify", "--expand")

# Commands that end the interactive session
EXIT_COMMANDS = ("exit", "quit")

# Errors with a message meant for the user
APP_ERRORS = (
    InvalidCommand,
    InvalidURL,
    CompleteUrlNotFound,
    ShortenedUrlExpired,
    ShortUrlGenerationFailed,
)


def connect():
    """
    Connects to MongoDB. The connection string is read from the
    MONGODB_URI environment variable; a database name in it takes
    precedence over DEFAULT_DB_NAME

    Raises
    ------
    ConfigurationError, ValueError
        If the connection string is invalid
    """
    mongoengine.connect(
        host=os.environ.get(MONGODB_URI_ENV_VAR) or DEFAULT_MONGODB_URI,
        db=DEFAULT_DB_NAME,
        serverSelectionTimeoutMS=DB_TIMEOUT_MS,
    )


def expires_in_seconds(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number <= 0:
        raise argparse.ArgumentTypeError(
            f"must be a positive integer, got {value!r}"
        )
    if number > MAX_EXPIRES_IN:
        raise argparse.ArgumentTypeError(
            f"must be at most {MAX_EXPIRES_IN} seconds, got {value!r}"
        )
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="url-shortener",
        usage=(
            "%(prog)s [-h] [--minify=URL | --expand=URL] "
            "[--expires-in SECONDS]"
        ),
        description=(
            "Shorten a URL or expand a shortened URL. "
            "Without --minify or --expand, starts an interactive session."
        ),
        # e.g. --min=URL is not accepted
        allow_abbrev=False,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--minify",
        metavar="URL",
        help="complete URL to shorten, as --minify=URL",
    )
    group.add_argument(
        "--expand",
        metavar="URL",
        help="shortened URL to expand, as --expand=URL",
    )
    parser.add_argument(
        "--expires-in",
        metavar="SECONDS",
        type=expires_in_seconds,
        help=(
            "seconds before a new shortened URL expires "
            f"(default: ${EXPIRES_IN_ENV_VAR} or {DEFAULT_EXPIRES_IN})"
        ),
    )
    # argparse also accepts "--minify URL": only "--minify=URL" is allowed
    for arg in sys.argv[1:] if argv is None else argv:
        if arg in URL_OPTIONS:
            parser.error(f"argument {arg}: use the form {arg}=URL")
    args = parser.parse_args(argv)

    if args.expires_in is not None and args.expand is not None:
        parser.error("argument --expires-in: not allowed with --expand")
    if args.expires_in is None:
        env_value = os.environ.get(EXPIRES_IN_ENV_VAR)
        if env_value:
            try:
                args.expires_in = expires_in_seconds(env_value)
            except argparse.ArgumentTypeError as e:
                parser.error(f"environment variable {EXPIRES_IN_ENV_VAR}: {e}")
        else:
            args.expires_in = DEFAULT_EXPIRES_IN
    return args


def run_command(
    prefix: str, url: str, expires_in: int = DEFAULT_EXPIRES_IN
) -> str:
    """
    Runs a minify or expand command

    Parameters
    ----------
    prefix
        Either "--minify" or "--expand"
    url
        URL to minify or expand
    expires_in
        Seconds before a new shortened url expires, used by "--minify"

    Returns
    -------
    result
        The shortened url for "--minify", the complete url for "--expand"
    """
    validate_url(url=url, prefix=prefix)
    url = normalize_url(url)
    if prefix == "--minify":
        return ShorteningUrlService.get_shortened_url(
            complete_url=url, expires_in=expires_in
        )
    return ShorteningUrlService.expand_url(shortened_url=url)


def interactive_session(expires_in: int = DEFAULT_EXPIRES_IN):
    print('Type "exit" to quit.')
    while True:
        try:
            command = input("Insert command: ")
            if command.strip().lower() in EXIT_COMMANDS:
                return
            prefix, url = process_input(command)
            print(run_command(prefix=prefix, url=url, expires_in=expires_in))
        except APP_ERRORS as e:
            print(e)
        except ConnectionFailure:
            # the session goes on: MongoDB may be started in the meantime
            print(DB_NOT_REACHABLE_MESSAGE)
        except PyMongoError as e:
            # e.g. authentication failed
            print(f"Database error: {e}")
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D (Ctrl+Z on Windows) or Ctrl+C: quit on a new line
            print()
            return


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # connect to mongo DB
    try:
        connect()
    except (ConfigurationError, ValueError) as e:
        print(f"Invalid {MONGODB_URI_ENV_VAR}: {e}", file=sys.stderr)
        return 1

    if args.minify is None and args.expand is None:
        interactive_session(expires_in=args.expires_in)
        return 0

    if args.minify is not None:
        prefix, url = "--minify", args.minify
    else:
        prefix, url = "--expand", args.expand
    try:
        print(
            run_command(
                prefix=prefix, url=url.strip(), expires_in=args.expires_in
            )
        )
    except APP_ERRORS as e:
        print(e, file=sys.stderr)
        return 1
    except ConnectionFailure:
        print(DB_NOT_REACHABLE_MESSAGE, file=sys.stderr)
        return 1
    except PyMongoError as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
