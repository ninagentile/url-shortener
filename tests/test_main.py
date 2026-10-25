from unittest import mock

import pytest

import main
from url_shortener.db_mocker import DbMocker
from url_shortener.service import (
    CODE_LENGTH,
    SHORT_URL_DOMAIN,
    ShortenedUrlCreator,
)

COMPLETE_URL = "https://www.example.com/path?q=search"


@pytest.fixture(autouse=True)
def no_real_connection(monkeypatch):
    # tests use the mongomock connection opened in conftest.py
    monkeypatch.setattr(main, "connect", lambda: None)


def run_main(capsys, argv: list[str]) -> tuple[int, str, str]:
    exit_code = main.main(argv)
    captured = capsys.readouterr()
    return exit_code, captured.out.strip(), captured.err.strip()


class TestParseArgs:
    def test_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(["--help"])
        assert exc_info.value.code == 0
        assert "--minify URL" in capsys.readouterr().out

    def test_minify_and_expand_together(self):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(
                ["--minify=https://www.a.com", "--expand=https://www.b.com"]
            )
        assert exc_info.value.code == 2

    def test_unknown_argument(self):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(["--foo=bar"])
        assert exc_info.value.code == 2

    @pytest.mark.parametrize(
        "argv", [[f"--minify={COMPLETE_URL}"], ["--minify", COMPLETE_URL]]
    )
    def test_minify_forms(self, argv):
        args = main.parse_args(argv)
        assert args.minify == COMPLETE_URL
        assert args.expand is None


class TestMinify:
    def test_minify(self, capsys):
        exit_code, out, err = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        assert exit_code == 0
        assert err == ""
        prefix, code = out.rsplit("/", 1)
        assert prefix == SHORT_URL_DOMAIN
        assert len(code) == CODE_LENGTH

    def test_same_url_returns_same_short(self, capsys):
        _, first_short, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        _, second_short, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        assert first_short == second_short

    @pytest.mark.parametrize(
        "equivalent_url",
        [
            "https://www.example.com/",
            "HTTPS://WWW.EXAMPLE.COM",
            "https://www.example.com:443",
        ],
    )
    def test_equivalent_urls_return_same_short(self, capsys, equivalent_url):
        _, short, _ = run_main(capsys, ["--minify=https://www.example.com"])
        _, other_short, _ = run_main(capsys, [f"--minify={equivalent_url}"])
        assert other_short == short

    def test_different_paths_return_different_shorts(self, capsys):
        _, short, _ = run_main(capsys, ["--minify=https://www.example.com/a"])
        _, other_short, _ = run_main(
            capsys, ["--minify=https://www.example.com/A"]
        )
        assert other_short != short

    def test_url_with_spaces(self, capsys):
        _, short, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        exit_code, out, _ = run_main(capsys, [f"--minify=  {COMPLETE_URL}  "])
        assert exit_code == 0
        assert out == short

    def test_expired_url_is_minified_again(self, capsys):
        old_short = f"{SHORT_URL_DOMAIN}/expired"
        DbMocker.mock_shortened_url(
            is_expired=True,
            complete_url=COMPLETE_URL,
            shortened_url=old_short,
        )
        exit_code, out, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        assert exit_code == 0
        assert out != old_short

    @pytest.mark.parametrize(
        "url, message",
        [
            ("notaurl", "Invalid URL"),
            ("", "Invalid URL"),
            ("ftp://www.a.com", "Invalid URL"),
            (f"{SHORT_URL_DOMAIN}/abc1234", "already shortened"),
        ],
    )
    def test_invalid_url(self, capsys, url, message):
        exit_code, out, err = run_main(capsys, [f"--minify={url}"])
        assert exit_code == 1
        assert out == ""
        assert message in err

    def test_short_url_generation_failed(self, capsys):
        DbMocker.mock_shortened_url(
            is_expired=False,
            complete_url="https://www.a.com",
            shortened_url=f"{SHORT_URL_DOMAIN}/taken00",
        )
        with mock.patch.object(
            ShortenedUrlCreator,
            "shortened_url",
            return_value=f"{SHORT_URL_DOMAIN}/taken00",
        ):
            exit_code, out, err = run_main(
                capsys, ["--minify=https://www.b.com"]
            )
        assert exit_code == 1
        assert out == ""
        assert "Could not generate a unique shortened url" in err


class TestExpand:
    def test_expand(self, capsys):
        _, short, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        exit_code, out, err = run_main(capsys, [f"--expand={short}"])
        assert exit_code == 0
        assert out == COMPLETE_URL
        assert err == ""

    def test_expand_returns_normalized_url(self, capsys):
        _, short, _ = run_main(capsys, ["--minify=HTTPS://WWW.EXAMPLE.COM"])
        _, out, _ = run_main(capsys, [f"--expand={short}"])
        assert out == "https://www.example.com/"

    def test_expand_with_uppercase_domain(self, capsys):
        _, short, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        code = short.rsplit("/", 1)[1]
        exit_code, out, _ = run_main(
            capsys, [f"--expand=HTTPS://MyUrlShortener.com/{code}"]
        )
        assert exit_code == 0
        assert out == COMPLETE_URL

    def test_expand_not_found(self, capsys):
        exit_code, out, err = run_main(
            capsys, [f"--expand={SHORT_URL_DOMAIN}/fstp4"]
        )
        assert exit_code == 1
        assert out == ""
        assert "No complete url found" in err

    def test_expand_expired(self, capsys):
        short = f"{SHORT_URL_DOMAIN}/expired"
        DbMocker.mock_shortened_url(
            is_expired=True,
            complete_url=COMPLETE_URL,
            shortened_url=short,
        )
        exit_code, out, err = run_main(capsys, [f"--expand={short}"])
        assert exit_code == 1
        assert out == ""
        assert "is expired" in err

    def test_expand_invalid_url(self, capsys):
        exit_code, out, err = run_main(capsys, ["--expand=notaurl"])
        assert exit_code == 1
        assert out == ""
        assert "Invalid URL" in err


class TestInteractiveSession:
    def run_session(self, monkeypatch, capsys, commands: list[str]) -> str:
        """
        Runs the interactive session with the given commands and returns
        its output. The session ends when the commands are over
        """
        inputs = iter(commands)

        def fake_input(prompt=""):
            try:
                return next(inputs)
            except StopIteration:
                raise EOFError from None

        monkeypatch.setattr("builtins.input", fake_input)
        with pytest.raises(EOFError):
            main.main([])
        return capsys.readouterr().out

    def test_minify_and_expand(self, monkeypatch, capsys):
        _, short, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        out = self.run_session(
            monkeypatch,
            capsys,
            [f"--minify={COMPLETE_URL}", f"--expand={short}"],
        )
        assert out.splitlines() == [short, COMPLETE_URL]

    def test_errors_do_not_stop_the_session(self, monkeypatch, capsys):
        out = self.run_session(
            monkeypatch,
            capsys,
            [
                "",
                "help",
                "--minify=notaurl",
                f"--expand={SHORT_URL_DOMAIN}/fstp4",
                f"--minify={COMPLETE_URL}",
            ],
        )
        lines = out.splitlines()
        assert lines[0] == "Invalid command, please try again"
        assert lines[1] == "Invalid command, please try again"
        assert "Invalid URL" in lines[2]
        assert "No complete url found" in lines[3]
        # the last command still works after the errors
        assert lines[4].startswith(SHORT_URL_DOMAIN)
