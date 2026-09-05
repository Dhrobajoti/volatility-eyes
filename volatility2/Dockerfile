# volatility2 (2.6.1) requires Python 2.7, which reached EOL in Jan 2020 -
# see volatility2/README.md for why this exists anyway (some memory images defeat
# volatility3's automagic symbol resolution outright; volatility2's static
# profile system handles them fine) and how it's isolated from the rest of
# the stack (separate container, no inbound exposure, only ever fed image
# files the investigator already uploaded - never untrusted network input).
#
# Debian stretch (the last Debian release with default python2 packaging)
# is itself EOL and removed from the normal mirrors - apt must point at
# archive.debian.org instead, confirmed necessary by hitting the plain
# `apt-get update` 404s directly before writing this.

# ---- builder: git + gcc (for distorm3's C extension) - measured at 237MB,
# the single largest layer in the image, and entirely unneeded once the
# clone and pip install are done. Same lesson as volatility3/Dockerfile.
FROM python:2.7.18-slim-stretch AS builder

RUN printf 'deb http://archive.debian.org/debian stretch main\ndeb http://archive.debian.org/debian-security stretch/updates main\n' > /etc/apt/sources.list \
    && apt-get update -qq \
    && apt-get install -y -qq --allow-unauthenticated \
        git \
        build-essential \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

ARG VOLATILITY2_TAG=2.6.1
RUN git clone --branch ${VOLATILITY2_TAG} --depth 1 \
    https://github.com/volatilityfoundation/volatility.git /opt/volatility2 \
    # .git (the shallow clone's own history) is never read at runtime -
    # only the source tree is.
    && rm -rf /opt/volatility2/.git

# pycryptodome (not pycryptodomex) installs as the `Crypto` package, which is
# what volatility2's registry/hashdump/etc. plugins import - confirmed this
# is the variant needed by actually hitting `ImportError: No module named
# Crypto.Hash` with plain volatility2 and fixing it here.
# distorm3 enables disassembly-dependent plugins (malfind, ssdt, apihooks).
RUN pip install --no-cache-dir --target=/opt/pydeps \
        bottle==0.12.25 \
        pycryptodome==3.9.9 \
        distorm3==3.4.4 \
        subprocess32==3.5.4 \
    # Crypto/SelfTest is pycryptodome's own test-vector suite (34MB of the
    # package's 39MB installed size - measured directly) - it's importable
    # but only ever invoked by `python -m Crypto.SelfTest`, never by
    # anything volatility2 actually calls at runtime.
    && rm -rf /opt/pydeps/Crypto/SelfTest

# ---- runtime: no compiler, no git - just Python 2.7, the installed
# packages, and volatility2's own source (which is pure Python, needs no
# compiler itself; only its optional distorm3 dependency did).
FROM python:2.7.18-slim-stretch

COPY --from=builder /opt/volatility2 /opt/volatility2
COPY --from=builder /opt/pydeps /usr/local/lib/python2.7/site-packages

WORKDIR /app
COPY app .

ENV PYTHONUNBUFFERED=1
EXPOSE 8200
CMD ["python", "main.py"]
