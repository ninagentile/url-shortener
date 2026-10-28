FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install only the runtime dependencies, with an empty package so that
# this layer is rebuilt only when pyproject.toml changes
COPY pyproject.toml README.md ./
RUN mkdir -p src/url_shortener \
    && touch src/url_shortener/__init__.py \
    && pip install .

# Install the real package, without reinstalling the dependencies
COPY src ./src
RUN pip install --no-deps --force-reinstall .

COPY main.py ./

# Run as a non-root user
RUN useradd --create-home --uid 1000 app
USER app

ENTRYPOINT ["python", "main.py"]
