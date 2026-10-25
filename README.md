# url-shortener
Python command line tool that performs URL shortening and expansion.

- `--minify` turns a complete URL into a short one, e.g.
  `https://myurlshortener.com/aZ3kP9x`.
- `--expand` turns a short URL back into the complete one.
- Short URLs expire after a configurable number of seconds.

Short codes are generated with Python's standard library only
(`secrets`): no URL-shortening libraries are used.

## Run with Docker

The easiest way to run the tool: only [Docker](https://docs.docker.com/get-docker/)
is needed, and MongoDB runs in its own container.

```bash
docker compose up -d mongo                 # start MongoDB
docker compose run --rm app --minify=https://www.example.com/path?q=search
docker compose run --rm app --expand=https://myurlshortener.com/aZ3kP9x
docker compose run --rm app                # interactive mode
docker compose down                        # stop MongoDB (-v also deletes the data)
```

The first `run` builds the image. The data is kept in the `mongo-data`
volume between runs. To change the expiration time, pass
`--expires-in=SECONDS` or set `URL_SHORTENER_EXPIRES_IN` before
`docker compose run`.

## Run locally

### Requirements

- Python 3.11+
- MongoDB, by default on `localhost:27017` (see
  [Settings](#settings) to use another one)

### Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"        # drop [dev] if you don't need test tools
```

## Usage

The examples use `python main.py`; with Docker, replace it with
`docker compose run --rm app`.

```bash
$ python main.py --minify=https://www.example.com/path?q=search
https://myurlshortener.com/aZ3kP9x

$ python main.py --expand=https://myurlshortener.com/aZ3kP9x
https://www.example.com/path?q=search

$ python main.py --expand=https://myurlshortener.com/fstp4
No complete url found for short URL: https://myurlshortener.com/fstp4
```

Both `--minify=URL` and `--minify URL` work; `--minify` and `--expand`
can't be used together. Run `python main.py --help` for the full usage.

### Expiration time

New short URLs expire after 3600 seconds by default. To change it, use the
`--expires-in` option or the `URL_SHORTENER_EXPIRES_IN` environment
variable (the option wins if both are set):

```bash
$ python main.py --minify=https://www.example.com --expires-in=60

$ export URL_SHORTENER_EXPIRES_IN=60       # Windows PowerShell: $env:URL_SHORTENER_EXPIRES_IN=60
$ python main.py --minify=https://www.example.com
```

The value must be a positive integer. `--expires-in` can't be used with
`--expand`, and it only applies to new short URLs: if the URL already has a
valid short URL, that one is returned with its original expiration.

Results are printed on stdout; errors are printed on stderr. Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Invalid URL, short URL not found or expired, database not reachable |
| 2 | Invalid arguments |

### Interactive mode

Without `--minify` or `--expand` the tool starts an interactive session,
which reads one command at a time. `--expires-in` can be used here too,
e.g. `python main.py --expires-in=60`.

```
$ python main.py
Type "exit" to quit.
Insert command: --minify=https://www.example.com
https://myurlshortener.com/Lt0MCuJ
Insert command: --expand=https://myurlshortener.com/Lt0MCuJ
https://www.example.com/
Insert command: exit
```

To quit, type `exit` or `quit`, or press Ctrl+C or Ctrl+D (Ctrl+Z and
Enter on Windows).

## How it works

- **Normalization**: URLs are normalized before being saved or searched.
  Scheme and host are lowercased, the default port is removed and an empty
  path becomes `/`. This way `https://a.com`, `https://a.com/` and
  `HTTPS://A.com:443` all get the same short URL. Path, query and fragment
  are case sensitive, so they are kept as they are.
- **Minify**: if the URL already has a short URL that hasn't expired, the
  same short URL is returned. Otherwise a new one is created, with a random
  7-character code (`a-z`, `A-Z`, `0-9`).
- **Expand**: returns the complete URL. If the short URL doesn't exist or
  has expired, an error message is printed instead.
- **Expiration**: a short URL expires after the
  [expiration time](#expiration-time) given at its creation. Once expired,
  `--expand` reports it as expired, and `--minify` of the same URL creates
  a new short URL.
- **Cleanup**: MongoDB deletes expired short URLs 24 hours after their
  expiration, through a TTL index. After that, `--expand` reports them as
  not found, and their codes can be reused.
- **Uniqueness**: a unique index on the short URL prevents duplicates. If a
  generated code is already taken, a new one is generated (up to 5
  attempts).
- **Time zone**: all times are stored and compared in UTC.

### Settings

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017/` | MongoDB connection string. The database is the one in the string, or `url_shortener` if it has none |
| `URL_SHORTENER_EXPIRES_IN` | `3600` | See [expiration time](#expiration-time) |

If MongoDB isn't reachable within 3 seconds, the tool prints
`Database not reachable` and exits with code 1. In interactive mode the
session goes on, so the command can be retried once MongoDB is up.

Other settings are constants in the code:

| Constant | File | Default | Meaning |
|---|---|---|---|
| `DEFAULT_EXPIRES_IN` | `src/url_shortener/service.py` | `3600` | Default seconds before a short URL expires |
| `CODE_LENGTH` | `src/url_shortener/service.py` | `7` | Length of the short code |
| `SHORT_URL_DOMAIN` | `src/url_shortener/service.py` | `https://myurlshortener.com` | Domain of the short URLs |
| `EXPIRED_RETENTION_SECONDS` | `src/url_shortener/database/entities.py` | `86400` | Seconds an expired short URL is kept before deletion |

MongoDB doesn't update an existing TTL index on its own: after changing
`EXPIRED_RETENTION_SECONDS`, drop the old index with
`db.shortened_url.dropIndex("expiration_time_1")` in `mongosh`. It will be
created again on the next run.

## Project structure

```
├── .github/workflows/ci.yml   # CI: lint, tests on Python 3.11 and 3.12, Docker
├── Dockerfile                 # image of the tool
├── docker-compose.yml         # tool + MongoDB
├── main.py                    # command line entry point
├── src/url_shortener/
│   ├── database/
│   │   ├── entities.py        # MongoDB document and indexes
│   │   └── queries.py         # database queries
│   ├── service.py             # minify / expand logic
│   ├── validation.py          # command and URL validation
│   ├── exceptions.py          # custom exceptions
│   ├── dtos.py                # data transfer objects
│   ├── time_utils.py          # UTC time helper
│   └── db_mocker.py           # helpers to create test documents
├── tests/                     # automated tests
├── scripts/                   # utility scripts
└── pyproject.toml             # packaging, dependencies and tool configuration
```

## Running tests

```bash
pytest
```

The tests use an in-memory database ([mongomock](https://github.com/mongomock/mongomock)),
so MongoDB doesn't need to be running.

To check the code style:

```bash
ruff check .
```

## Known limitations

- Two simultaneous `--minify` of the same URL can create two different
  short URLs.
