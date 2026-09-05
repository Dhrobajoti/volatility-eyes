# Build context is the project root (see docker-compose.yml) so this
# Dockerfile can reach both the volatility3/ service package and shared
# docker/ assets.

# ---- builder: has the C toolchain + git, neither of which the running
# container needs - only the installed Python packages get carried forward.
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# volatility3 is a third-party upstream project (Volatility Foundation,
# Volatility Software License 1.0) - it is not vendored or submoduled into
# this repo (see README), it's cloned fresh here and installed normally
# (not editable), so the clone can be discarded once installed. Pinned to a
# specific commit for reproducible builds; bump deliberately, not implicitly.
ARG VOLATILITY3_COMMIT=9e4931687b947ebfdfcea50ee574b9130004ea01
# --no-compile: skip .pyc generation at install time - measured at 48MB of
# __pycache__ across the venv (16% of the whole image), pure dead weight
# since Python transparently compiles+caches on first import anyway, so
# there's no runtime behavior difference, just a one-time (imperceptible)
# compile cost the first time each module is imported.
RUN git clone https://github.com/volatilityfoundation/volatility3.git /tmp/volatility3 \
    && cd /tmp/volatility3 \
    && git checkout ${VOLATILITY3_COMMIT} \
    && pip install --no-cache-dir --no-compile ".[full]" \
    && rm -rf /tmp/volatility3

WORKDIR /app
COPY volatility3/pyproject.toml /app/volatility3/pyproject.toml
COPY volatility3/app /app/volatility3/app
RUN pip install --no-cache-dir --no-compile -e "/app/volatility3"

# Runtime never installs packages (the venv is COPY'd as a finished
# artifact), so pip itself - 13MB, mostly its own bundled `_vendor` copies of
# other libraries - is dead weight; same for pycryptodome's SelfTest (test
# vectors, 3.4MB, never invoked outside `python -m Crypto.SelfTest`) and the
# test-only helper submodules a few libraries ship inside their normal
# package (never imported by application code, only by that library's own
# test suite or a downstream project's pytest plugin, which this app isn't).
# The trailing find is a catch-all for any __pycache__ that --no-compile
# above didn't cover (e.g. written by a package's own install-time subprocess).
RUN rm -rf \
        /opt/venv/lib/python3.12/site-packages/pip \
        /opt/venv/lib/python3.12/site-packages/pip-*.dist-info \
        /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.12 \
        /opt/venv/lib/python3.12/site-packages/Crypto/SelfTest \
        /opt/venv/lib/python3.12/site-packages/greenlet/tests \
        /opt/venv/lib/python3.12/site-packages/alembic/testing \
        /opt/venv/lib/python3.12/site-packages/sqlalchemy/testing \
        /opt/venv/lib/python3.12/site-packages/certifi/tests \
        /opt/venv/lib/python3.12/site-packages/mako/testing \
    && find /opt/venv -name '__pycache__' -type d -exec rm -rf {} +

# ---- runtime: no compiler, no git, just the venv and the app source.
FROM python:3.12-slim

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" PYTHONUNBUFFERED=1

WORKDIR /app
COPY volatility3/pyproject.toml /app/volatility3/pyproject.toml
COPY volatility3/app /app/volatility3/app
COPY volatility3/alembic.ini /app/volatility3/alembic.ini
COPY volatility3/alembic /app/volatility3/alembic

WORKDIR /app/volatility3

EXPOSE 8000
