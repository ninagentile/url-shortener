import mongoengine

from url_shortener.exceptions import InvalidCommand
from url_shortener.service import ShorteningUrlService


def connect():
    mongoengine.connect(
        host="mongodb://localhost:27017/",
        db="url_shortener",
    )


def validate_url(url: str):
    # TODO: use url validation
    assert len(url) > 0


def process_input(command: str) -> tuple[str, str]:
    try:
        prefix, url = command.split("=")
        assert prefix in ["--minify", "--expand"]
        validate_url(url=url)
        return prefix, url
    except Exception:
        raise InvalidCommand("Command is invalid, please try again")


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
        except InvalidCommand:
            print("Invalid command, please try again")
