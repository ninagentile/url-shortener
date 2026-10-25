from urllib.parse import urlparse, urlsplit, urlunsplit

from url_shortener.exceptions import InvalidCommand, InvalidURL
from url_shortener.service import SHORT_URL_DOMAIN

DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_url(url: str) -> str:
    """
    Returns the normalized version of a url, so that equivalent urls are
    saved and searched in the same way. Scheme and host are lowercased,
    the default port is removed and an empty path becomes "/". Path,
    query and fragment are kept as they are, since they are case
    sensitive

    Parameters
    ----------
    url
        Valid http or https url

    Returns
    -------
    normalized_url
        Normalized url

    Raises
    ------
    InvalidURL
        If the url has an invalid port
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    try:
        port = parts.port
    except ValueError:
        raise InvalidURL(f"Invalid URL: {url}") from None

    host = parts.hostname
    if ":" in host:
        # IPv6 address
        host = f"[{host}]"
    netloc = host
    if port is not None and port != DEFAULT_PORTS[scheme]:
        netloc = f"{netloc}:{port}"
    # keep user info (user:password@) as it is
    user_info, at, _ = parts.netloc.rpartition("@")
    if at:
        netloc = f"{user_info}@{netloc}"

    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, parts.fragment))


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
    return prefix, url
