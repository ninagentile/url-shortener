# url-shortener
Python command line tool that performs URL shortening and expansion.

- `--minify` turns a complete URL into a short one, e.g.
  `https://myurlshortener.com/aZ3kP9x`.
- `--expand` turns a short URL back into the complete one.
- Short URLs expire after a configurable number of seconds.

## Requirements

- Python 3.11+
- MongoDB running on `localhost:27017` (the tool uses the `url_shortener`
  database)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"        # drop [dev] if you don't need test tools
```

## Usage

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

Results are printed on stdout; errors are printed on stderr. Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Invalid URL, short URL not found or expired |
| 2 | Invalid arguments |

### Interactive mode

Without arguments the tool starts an interactive session, which reads one
command at a time:

```
$ python main.py
Insert command: --minify=https://www.example.com
https://myurlshortener.com/Lt0MCuJ
Insert command: --expand=https://myurlshortener.com/Lt0MCuJ
https://www.example.com
```

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
- **Expiration**: a short URL expires `EXPIRES_IN` seconds after its
  creation. Once expired, `--expand` reports it as expired, and
  `--minify` of the same URL creates a new short URL.
- **Cleanup**: MongoDB deletes expired short URLs 24 hours after their
  expiration, through a TTL index. After that, `--expand` reports them as
  not found, and their codes can be reused.
- **Uniqueness**: a unique index on the short URL prevents duplicates. If a
  generated code is already taken, a new one is generated (up to 5
  attempts).
- **Time zone**: all times are stored and compared in UTC.

### Settings

The settings are constants in the code:

| Constant | File | Default | Meaning |
|---|---|---|---|
| `EXPIRES_IN` | `src/url_shortener/service.py` | `30` | Seconds before a short URL expires |
| `CODE_LENGTH` | `src/url_shortener/service.py` | `7` | Length of the short code |
| `SHORT_URL_DOMAIN` | `src/url_shortener/service.py` | `https://myurlshortener.com` | Domain of the short URLs |
| `EXPIRED_RETENTION_SECONDS` | `src/url_shortener/database/entities.py` | `86400` | Seconds an expired short URL is kept before deletion |

MongoDB doesn't update an existing TTL index on its own: after changing
`EXPIRED_RETENTION_SECONDS`, drop the old index with
`db.shortened_url.dropIndex("expiration_time_1")` in `mongosh`. It will be
created again on the next run.

## Project structure

```
├── .github/workflows/ci.yml   # CI: runs the tests on Python 3.11 and 3.12
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

- If MongoDB isn't reachable, the tool waits about 30 seconds and then
  stops with a traceback.
- Two simultaneous `--minify` of the same URL can create two different
  short URLs.
- In interactive mode, Ctrl+C or Ctrl+D/Ctrl+Z stops the tool with a
  traceback.
