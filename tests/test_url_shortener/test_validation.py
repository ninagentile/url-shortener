import pytest

from url_shortener.exceptions import InvalidCommand, InvalidURL
from url_shortener.validation import (
    normalize_url,
    validate_prefix,
    validate_url,
    process_input,
)

valid_urls = [
    "http://www.site.it",
    "https://www.site.it",
    "https://www.site.it/&query=1234",
]
invalid_urls = [
    "http://myurlshortener.com",
    "https://myurlshortener.com",
    "htp://www.site.it",
    "htps://www.site.it",
    "asdfg",
    "www.sdfg",
]
valid_prefixes = ["--minify", "--expand"]
invalid_prefixes = [
    "-minify",
    "-expand",
    "minify",
    "expand",
    "--minifi",
    "--expand12",
]


class TestValidateUrl:
    @pytest.mark.parametrize("url", valid_urls)
    def test_valid_url(self, url):
        validate_url(url, prefix="--minify")

    @pytest.mark.parametrize("url", invalid_urls)
    def test_invalid_url(self, url):
        with pytest.raises(InvalidURL):
            validate_url(url, prefix="--minify")


class TestNormalizeUrl:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://www.site.it", "https://www.site.it/"),
            ("https://www.site.it/", "https://www.site.it/"),
            ("HTTPS://WWW.Site.IT", "https://www.site.it/"),
            ("https://www.site.it:443/a", "https://www.site.it/a"),
            ("http://www.site.it:80/a", "http://www.site.it/a"),
            ("https://www.site.it:8080/a", "https://www.site.it:8080/a"),
            ("http://www.site.it:443/a", "http://www.site.it:443/a"),
            ("https://www.site.it?q=1", "https://www.site.it/?q=1"),
            ("https://www.site.it#top", "https://www.site.it/#top"),
            ("https://[::1]:8000", "https://[::1]:8000/"),
            ("https://User:Pass@WWW.site.it", "https://User:Pass@www.site.it/"),
        ],
    )
    def test_normalized(self, url, expected):
        assert normalize_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.site.it/Path/Page",
            "https://www.site.it/path?Q=Search&b=2",
            "https://www.site.it/path/#Section",
            "https://myurlshortener.com/aZ3kP9x",
        ],
    )
    def test_already_normalized(self, url):
        assert normalize_url(url) == url

    def test_invalid_port(self):
        with pytest.raises(InvalidURL):
            normalize_url("https://www.site.it:abc/")


class TestValidatePrefix:
    @pytest.mark.parametrize("prefix", valid_prefixes)
    def test_valid_prefix(self, prefix):
        validate_prefix(prefix)

    @pytest.mark.parametrize("prefix", invalid_prefixes)
    def test_invalid_prefix(self, prefix):
        with pytest.raises(InvalidCommand):
            validate_prefix(prefix)


class TestProcessInput:
    @pytest.mark.parametrize("url", valid_urls)
    @pytest.mark.parametrize("prefix", valid_prefixes)
    def test_valid_input(self, url, prefix):
        command = f"{prefix}={url}"
        process_input(command=command)

    @pytest.mark.parametrize("url", valid_urls)
    @pytest.mark.parametrize("prefix", valid_prefixes)
    def test_input_with_no_equal_sign(self, url, prefix):
        command = f"{prefix} {url}"
        with pytest.raises(InvalidCommand):
            process_input(command=command)

    @pytest.mark.parametrize("url", invalid_urls)
    @pytest.mark.parametrize("prefix", invalid_prefixes)
    def test_invalid_input(self, url, prefix):
        command = f"{prefix}={url}"
        with pytest.raises(InvalidCommand):
            process_input(command=command)
