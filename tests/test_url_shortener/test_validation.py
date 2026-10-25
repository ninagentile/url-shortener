import pytest

from url_shortener.exceptions import InvalidCommand, InvalidURL
from url_shortener.validation import (
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
        validate_url(url)

    @pytest.mark.parametrize(
        "url",
        ["-minify", "-expand", "minify", "expand", "--minifi", "--expand12"],
    )
    def test_valid_url(self, url):
        with pytest.raises(InvalidURL):
            validate_url(url)


class TestValidatePrefix:
    @pytest.mark.parametrize("prefix", valid_prefixes)
    def test_valid_prefix(self, prefix):
        validate_prefix(prefix)

    @pytest.mark.parametrize("prefix", invalid_prefixes)
    def test_valid_prefix(self, prefix):
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
    def test_input_with_no_equal_sign(self, url, prefix):
        command = f"{prefix}={url}"
        with pytest.raises(InvalidCommand):
            process_input(command=command)
