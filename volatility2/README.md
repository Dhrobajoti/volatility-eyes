# legacy

A [volatility2](https://github.com/volatilityfoundation/volatility) (2.6.1)
service for memory images volatility3's automagic can't handle - mainly
older Windows (XP/2003-era) captures. Not a stub: fully implemented and
verified against a real image that defeats volatility3 outright.

## Why this exists

volatility3 rebuilt symbol resolution around automatically downloading and
matching a PDB for the exact kernel build in the image. That's more robust
than volatility2's static profile system for modern Windows, but it can fail
completely on older/unusual images - not "some plugins don't work," but
every plugin, including `pslist`, failing with something like:

```
ValueError: Symbol type not in symbol_table_name1 SymbolTable: _ETHREAD
```

volatility2's profile system (`imageinfo` matches a known static profile
like `WinXPSP2x86` from KDBG signatures) has no equivalent failure mode for
these images - confirmed directly: an image that volatility3 rejected
outright profiled cleanly as `WinXPSP2x86`/`WinXPSP3x86` and ran `pslist`,
`connscan`, and others without issue.

## Isolation (why this doesn't put volatility3 or the rest of the stack at risk)

volatility2 requires Python 2.7, which reached end-of-life in January 2020 -
no further security patches, ever. That's a real tradeoff, made deliberately
rather than ignored, and contained as tightly as possible:

- **Separate container, separate process, separate codebase.** Nothing here
  is imported into the Python 3 backend/worker - the only interface is a
  small HTTP API (`/identify`, `/plugins`, `/run`), the same arm's-length
  relationship `insights` has with `ollama`.
- **No inbound exposure.** Not published to the host, reachable only from
  the internal Docker network, and only ever fed the path of an image the
  investigator already uploaded through the app - never arbitrary network
  input.
- **Read-only access to images.** Mounts `vol_storage` read-only; nothing
  here writes into the shared storage volume.
- **Failure is contained.** If this service is broken or removed entirely,
  volatility3 analysis (the default engine) is completely unaffected - it's
  a separate `Job.engine` code path in the backend, not a shared one.
- **Debian stretch, not something more recent.** stretch is the last Debian
  release with straightforward Python 2 packaging; even its own package
  mirrors are archived (`apt-get update` 404s against the default mirrors -
  confirmed directly), so the Dockerfile points at `archive.debian.org`
  explicitly rather than silently failing.

## Contract

`GET /health` -> `{"status": "ok"}`

`GET /plugins` -> `{"plugins": [{"name": "pslist", "description": "..."}, ...]}`
- Curated (see `app/catalog.py`), not auto-derived - volatility2 has no
  requirements-introspection API the way volatility3 does.

`POST /identify` - `{"image_path": "..."}` ->
`{"profiles": ["WinXPSP2x86", "WinXPSP3x86"], "raw": "<full imageinfo output>"}`
- Runs `vol.py -f <path> imageinfo` and parses the "Suggested Profile(s)"
  line. `raw` is kept for cases the parser doesn't handle cleanly.

`POST /run` - `{"image_path": "...", "profile": "WinXPSP2x86", "plugin_name": "connscan", "extra_args": ["-K", "some\\registry\\key"]}` ->
`{"output": "<plugin's own text output>", "returncode": 0}`
- Shells out to `vol.py -f <path> --profile=<profile> <plugin> <extra_args>`.
  `extra_args` is a raw passthrough of additional CLI flags for plugins that
  need them (e.g. `printkey` needs `-K`) - there's no structured
  parameter schema the way volatility3 plugins have.

Output is plain text (volatility2 has no reliable structured/JSON output
across its plugin catalog), rendered as preformatted text in the UI rather
than the interactive table volatility3 results get.

## Extending the plugin catalog

Edit `app/catalog.py`. Any volatility2 plugin works via `/run` as long as
its name is added there - the catalog is purely an allow-list, not a
technical restriction.
