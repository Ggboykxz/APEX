# APEX — npm package (`apex-ai`)

npm installer for the [APEX](https://apex-ai.dev) CLI. The APEX backend is
Python, so this package is a small **zero-dependency wrapper**: on first run
it provisions the `apex-ai` Python package (via `pipx`, `uv` or `pip`, in
that order of preference) and then runs the real CLI. After the first run you
never see this wrapper again.

## Install

```bash
npm install -g apex-ai
apex                      # TUI (default)
apex -p "Fix the bug"    # one-shot
```

No Node dependency is installed at runtime — Node is only used to bootstrap
the Python package on first run.

## How it resolves the binary

1. `APEX_BINARY` — explicit override, always wins.
2. An `apex` executable already on `PATH` (your own pip/pipx/uv install).
   The npm bin shim this package itself creates is recognized and skipped,
   so `npm install -g apex-ai` can never re-invoke its own wrapper.
3. First run: installs `apex-ai` (latest, or `APEX_VERSION` pin) with the
   best available strategy — `pipx` > `uv` > `python -m pip` — and runs it
   through the installer's own runner (`pipx run apex-ai`, `uv tool run
   apex-ai`, or `python -m apex`), so no `PATH` change is ever required.

On Windows, `.exe` targets are spawned directly. `.cmd`/`.bat`/`.ps1`
targets (pipx/conda shims) cannot receive multi-word arguments through a
plain `spawn`, so the wrapper delegates through a temporary `.bat` file
(`cmd /c`), written as UTF-8 with a `chcp 65001` preamble — arguments with
spaces, quotes and non-ASCII characters survive intact, and the exit code
propagates.

## Environment variables

| Variable | Effect |
|---|---|
| `APEX_BINARY` | Run this executable instead of resolving (e.g. a venv `bin/apex`). |
| `APEX_VERSION` | Pin the Python package version installed on first run (e.g. `2.5.0`). |
| `APEX_INSTALL_METHOD` | Force `pipx`, `uv`, `pip` or `auto` (default). |
| `APEX_SKIP_INSTALL` | `1` = fail fast with a hint instead of auto-installing. |

## Troubleshooting

- **No Python found** — install Python 3.11+, then `pipx`
  (`python3 -m pip install --user pipx`) or
  [`uv`](https://docs.astral.sh/uv/) and re-run `apex`.
- **First-run install failed** — install manually
  (`pipx install apex-ai` / `uv tool install apex-ai` /
  `python3 -m pip install apex-ai`) or point `APEX_BINARY` at your install.
- **Wrapper picks the wrong apex** — set `APEX_BINARY=/path/to/apex`.

## Development

```bash
cd integrations/npm
npm test            # node --test (no dependencies required)
```

Publishing happens from the `Release` workflow on `v*` tags and requires the
`NPM_TOKEN` repository secret. The release job fails when the package
version does not match the tag.
