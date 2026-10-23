# url-shortener
Python command line tool that performs URL shortening and expansion.

## Project structure

```
├── .github/
│   └── workflows/     # CI/CD (GitHub Actions: test, build, deploy)
├── docs/              # additional documentation
├── src/               # application source code
├── tests/             # automated tests
├── scripts/           # utility scripts (setup, migrations, etc.)
├── config/            # configuration files (no secrets!)
├── .gitignore
├── .env.example       # example of the required environment variables
├── pyproject.toml     # packaging, dependencies and tool configuration
└── README.md
```

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env           # then fill in the values
```

## Running tests

```bash
pytest
```
