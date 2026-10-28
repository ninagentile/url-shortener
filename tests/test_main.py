from datetime import timedelta
from unittest import mock

import pytest
from pymongo.errors import (
    InvalidURI,
    OperationFailure,
    ServerSelectionTimeoutError,
)

import main
from url_shortener.database.entities import ShortenedUrl
from url_shortener.db_mocker import DbMocker
from url_shortener.service import (
    CODE_LENGTH,
    DEFAULT_EXPIRES_IN,
    SHORT_URL_DOMAIN,
    ShortenedUrlCreator,
)
from url_shortener.time_utils import utc_now

COMPLETE_URL = "https://www.example.com/path?q=search"
# connect() is replaced in every test, it's tested through this reference
real_connect = main.connect


@pytest.fixture(autouse=True)
def no_real_connection(monkeypatch):
    # tests use the mongomock connection opened in conftest.py
    monkeypatch.setattr(main, "connect", lambda: None)
    # tests don't depend on the environment of the machine
    monkeypatch.delenv(main.EXPIRES_IN_ENV_VAR, raising=False)
    monkeypatch.delenv(main.MONGODB_URI_ENV_VAR, raising=False)


def run_main(capsys, argv: list[str]) -> tuple[int, str, str]:
    exit_code = main.main(argv)
    captured = capsys.readouterr()
    return exit_code, captured.out.strip(), captured.err.strip()


class TestParseArgs:
    def test_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(["--help"])
        assert exc_info.value.code == 0
        assert "--minify=URL" in capsys.readouterr().out

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

    def test_minify_with_equal_sign(self):
        args = main.parse_args([f"--minify={COMPLETE_URL}"])
        assert args.minify == COMPLETE_URL
        assert args.expand is None

    @pytest.mark.parametrize(
        "argv",
        [
            ["--minify", COMPLETE_URL],
            ["--expand", f"{SHORT_URL_DOMAIN}/abc1234"],
            ["--expires-in=10", "--minify", COMPLETE_URL],
        ],
    )
    def test_url_without_equal_sign(self, capsys, argv):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(argv)
        assert exc_info.value.code == 2
        assert f"use the form {argv[-2]}=URL" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "argv",
        [[f"--min={COMPLETE_URL}"], [f"--exp={SHORT_URL_DOMAIN}/abc1234"]],
    )
    def test_abbreviation_not_allowed(self, argv):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(argv)
        assert exc_info.value.code == 2


class TestExpiresIn:
    def seconds_left(self) -> float:
        doc = ShortenedUrl.objects.get(complete_url=COMPLETE_URL)
        return (doc.expiration_time - utc_now()).total_seconds()

    def test_default(self):
        args = main.parse_args([f"--minify={COMPLETE_URL}"])
        assert args.expires_in == DEFAULT_EXPIRES_IN

    def test_option(self, capsys):
        exit_code, _, _ = run_main(
            capsys, [f"--minify={COMPLETE_URL}", "--expires-in=10"]
        )
        assert exit_code == 0
        assert 5 < self.seconds_left() <= 10

    def test_environment_variable(self, capsys, monkeypatch):
        monkeypatch.setenv(main.EXPIRES_IN_ENV_VAR, "20")
        run_main(capsys, [f"--minify={COMPLETE_URL}"])
        assert 15 < self.seconds_left() <= 20

    def test_option_overrides_environment_variable(self, monkeypatch):
        monkeypatch.setenv(main.EXPIRES_IN_ENV_VAR, "20")
        args = main.parse_args([f"--minify={COMPLETE_URL}", "--expires-in=10"])
        assert args.expires_in == 10

    def test_environment_variable_with_expand(self, monkeypatch):
        monkeypatch.setenv(main.EXPIRES_IN_ENV_VAR, "20")
        args = main.parse_args([f"--expand={SHORT_URL_DOMAIN}/abc1234"])
        assert args.expand == f"{SHORT_URL_DOMAIN}/abc1234"

    def test_interactive_session(self, capsys, monkeypatch):
        inputs = iter([f"--minify={COMPLETE_URL}"])

        def fake_input(prompt=""):
            try:
                return next(inputs)
            except StopIteration:
                raise EOFError from None

        monkeypatch.setattr("builtins.input", fake_input)
        assert main.main(["--expires-in=10"]) == 0
        assert 5 < self.seconds_left() <= 10

    @pytest.mark.parametrize("value", ["0", "-5", "abc", "1.5", ""])
    def test_invalid_option(self, capsys, value):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(
                [f"--minify={COMPLETE_URL}", f"--expires-in={value}"]
            )
        assert exc_info.value.code == 2
        assert "must be a positive integer" in capsys.readouterr().err

    def test_too_large(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(
                [
                    f"--minify={COMPLETE_URL}",
                    f"--expires-in={main.MAX_EXPIRES_IN + 1}",
                ]
            )
        assert exc_info.value.code == 2
        assert "must be at most" in capsys.readouterr().err

    def test_max_value(self, capsys):
        exit_code, _, _ = run_main(
            capsys,
            [
                f"--minify={COMPLETE_URL}",
                f"--expires-in={main.MAX_EXPIRES_IN}",
            ],
        )
        assert exit_code == 0

    @pytest.mark.parametrize("value", ["0", "-5", "abc"])
    def test_invalid_environment_variable(self, capsys, monkeypatch, value):
        monkeypatch.setenv(main.EXPIRES_IN_ENV_VAR, value)
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args([f"--minify={COMPLETE_URL}"])
        assert exc_info.value.code == 2
        assert main.EXPIRES_IN_ENV_VAR in capsys.readouterr().err

    def test_not_allowed_with_expand(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main.parse_args(
                [f"--expand={SHORT_URL_DOMAIN}/abc1234", "--expires-in=10"]
            )
        assert exc_info.value.code == 2
        assert "not allowed with --expand" in capsys.readouterr().err

    def test_expired_after_custom_time(self, capsys):
        _, short, _ = run_main(
            capsys, [f"--minify={COMPLETE_URL}", "--expires-in=10"]
        )
        future = utc_now() + timedelta(seconds=11)
        with mock.patch("url_shortener.service.utc_now", return_value=future):
            exit_code, _, err = run_main(capsys, [f"--expand={short}"])
        assert exit_code == 1
        assert "is expired" in err


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
    def run_session(
        self, monkeypatch, capsys, commands: list
    ) -> tuple[int, list[str]]:
        """
        Runs the interactive session with the given commands and returns
        the exit code and the printed lines, without the initial hint. A
        command can also be an exception, raised when it's read. When the
        commands are over, EOF is reached
        """
        inputs = iter(commands)

        def fake_input(prompt=""):
            try:
                command = next(inputs)
            except StopIteration:
                raise EOFError from None
            if isinstance(command, BaseException):
                raise command
            return command

        monkeypatch.setattr("builtins.input", fake_input)
        exit_code = main.main([])
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == 'Type "exit" to quit.'
        return exit_code, lines[1:]

    def test_minify_and_expand(self, monkeypatch, capsys):
        _, short, _ = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        _, lines = self.run_session(
            monkeypatch,
            capsys,
            [f"--minify={COMPLETE_URL}", f"--expand={short}", "exit"],
        )
        assert lines == [short, COMPLETE_URL]

    @pytest.mark.parametrize("command", ["exit", "quit", "  EXIT  ", "Quit"])
    def test_exit_command(self, monkeypatch, capsys, command):
        exit_code, lines = self.run_session(
            monkeypatch,
            capsys,
            [command, f"--minify={COMPLETE_URL}"],
        )
        assert exit_code == 0
        # the commands after exit are not run
        assert lines == []
        assert ShortenedUrl.objects.count() == 0

    @pytest.mark.parametrize("exception", [EOFError(), KeyboardInterrupt()])
    def test_ctrl_d_and_ctrl_c(self, monkeypatch, capsys, exception):
        exit_code, lines = self.run_session(
            monkeypatch,
            capsys,
            [exception, f"--minify={COMPLETE_URL}"],
        )
        assert exit_code == 0
        # only the new line printed before quitting
        assert lines == [""]
        assert ShortenedUrl.objects.count() == 0

    def test_ctrl_c_while_running_a_command(self, monkeypatch, capsys):
        with mock.patch.object(
            main.ShorteningUrlService,
            "get_shortened_url",
            side_effect=KeyboardInterrupt,
        ):
            exit_code, lines = self.run_session(
                monkeypatch,
                capsys,
                [f"--minify={COMPLETE_URL}", f"--minify={COMPLETE_URL}"],
            )
        assert exit_code == 0
        assert lines == [""]

    def test_errors_do_not_stop_the_session(self, monkeypatch, capsys):
        _, lines = self.run_session(
            monkeypatch,
            capsys,
            [
                "",
                "help",
                "--minify=notaurl",
                f"--expand={SHORT_URL_DOMAIN}/fstp4",
                f"--minify={COMPLETE_URL}",
                "exit",
            ],
        )
        assert lines[0] == "Invalid command, please try again"
        assert lines[1] == "Invalid command, please try again"
        assert "Invalid URL" in lines[2]
        assert "No complete url found" in lines[3]
        # the last command still works after the errors
        assert lines[4].startswith(SHORT_URL_DOMAIN)


class TestDatabaseConnection:
    def connect_kwargs(self, monkeypatch) -> dict:
        fake_connect = mock.Mock()
        monkeypatch.setattr(main.mongoengine, "connect", fake_connect)
        real_connect()
        return fake_connect.call_args.kwargs

    def test_default_uri(self, monkeypatch):
        kwargs = self.connect_kwargs(monkeypatch)
        assert kwargs["host"] == main.DEFAULT_MONGODB_URI
        assert kwargs["db"] == main.DEFAULT_DB_NAME
        assert kwargs["serverSelectionTimeoutMS"] == main.DB_TIMEOUT_MS

    def test_uri_from_environment_variable(self, monkeypatch):
        monkeypatch.setenv(
            main.MONGODB_URI_ENV_VAR, "mongodb://mongo:27017/url_shortener"
        )
        kwargs = self.connect_kwargs(monkeypatch)
        assert kwargs["host"] == "mongodb://mongo:27017/url_shortener"

    @pytest.mark.parametrize(
        "error", [InvalidURI("bad uri"), ValueError("bad port")]
    )
    def test_invalid_uri(self, capsys, monkeypatch, error):
        monkeypatch.setattr(main, "connect", mock.Mock(side_effect=error))
        exit_code, out, err = run_main(capsys, [f"--minify={COMPLETE_URL}"])
        assert exit_code == 1
        assert out == ""
        assert f"Invalid {main.MONGODB_URI_ENV_VAR}" in err

    @pytest.mark.parametrize(
        "argv, method",
        [
            ([f"--minify={COMPLETE_URL}"], "get_shortened_url"),
            ([f"--expand={SHORT_URL_DOMAIN}/abc1234"], "expand_url"),
        ],
    )
    def test_database_not_reachable(self, capsys, argv, method):
        with mock.patch.object(
            main.ShorteningUrlService,
            method,
            side_effect=ServerSelectionTimeoutError("timeout"),
        ):
            exit_code, out, err = run_main(capsys, argv)
        assert exit_code == 1
        assert out == ""
        assert err == main.DB_NOT_REACHABLE_MESSAGE

    def test_database_error(self, capsys):
        with mock.patch.object(
            main.ShorteningUrlService,
            "get_shortened_url",
            side_effect=OperationFailure("Authentication failed"),
        ):
            exit_code, out, err = run_main(
                capsys, [f"--minify={COMPLETE_URL}"]
            )
        assert exit_code == 1
        assert out == ""
        assert err == "Database error: Authentication failed"

    def test_database_error_in_session(self, capsys, monkeypatch):
        inputs = iter([f"--minify={COMPLETE_URL}", f"--minify={COMPLETE_URL}"])

        def fake_input(prompt=""):
            try:
                return next(inputs)
            except StopIteration:
                raise EOFError from None

        monkeypatch.setattr("builtins.input", fake_input)
        # the first command fails, the second one works
        with mock.patch.object(
            main.ShorteningUrlService,
            "get_shortened_url",
            side_effect=[OperationFailure("Authentication failed"), "short"],
        ):
            exit_code = main.main([])
        lines = capsys.readouterr().out.splitlines()
        assert exit_code == 0
        assert lines[1] == "Database error: Authentication failed"
        assert lines[2] == "short"

    def test_database_not_reachable_in_session(self, capsys, monkeypatch):
        inputs = iter([f"--minify={COMPLETE_URL}", f"--minify={COMPLETE_URL}"])

        def fake_input(prompt=""):
            try:
                return next(inputs)
            except StopIteration:
                raise EOFError from None

        monkeypatch.setattr("builtins.input", fake_input)
        # the first command fails, the second one works
        with mock.patch.object(
            main.ShorteningUrlService,
            "get_shortened_url",
            side_effect=[ServerSelectionTimeoutError("timeout"), "short"],
        ):
            exit_code = main.main([])
        lines = capsys.readouterr().out.splitlines()
        assert exit_code == 0
        assert lines[1] == main.DB_NOT_REACHABLE_MESSAGE
        assert lines[2] == "short"
