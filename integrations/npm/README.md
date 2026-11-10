# APEX — npm package (`apex-ai`)

npm installer for the [APEX](https://apex-ai.dev) CLI. APEX ships through two
channels only: this **zero-dependency wrapper** and the prebuilt native
backend (`apex-rs`, Rust) attached to every GitHub release.

`npm install -g apex-ai` installs **everything in one shot**:

1. the verified native backend (`apex-rs`) in `~/.apex/bin`
2. the Ink + React TUI frontend in `~/.apex/tui-frontend` (dependencies
   installed with bun or npm)

After installation, run `apex` to launch the TUI connected to the native
backend, or `apex serve` / `apex run …` for headless mode.

## Install

```bash
npm install -g apex-ai
apex                    # TUI (default), connected to the native backend
apex run "Fix the bug"  # one-shot through the native backend
apex serve --port 8765  # headless HTTP API
```

No Node dependency is installed at runtime — Node only runs this wrapper.

## How it resolves the binary

1. `APEX_BINARY` — explicit override, always wins.
2. An `apex` executable already on `PATH` (source checkout or custom
   install). The npm bin shim this package itself creates is recognized and
   skipped, so `npm install -g apex-ai` can never re-invoke its own wrapper.
3. The native backend: `apex-rs` on `PATH`, the managed
   `~/.apex/bin/apex-rs`, or a checksum-verified download from the latest
   GitHub release (or `APEX_VERSION`).

The TUI frontend is provisioned in `~/.apex/tui-frontend` (override with
`APEX_TUI_DIR`) and its dependencies are installed with bun or npm.

On Windows, `.exe` targets are spawned directly. `.cmd`/`.bat`/`.ps1`
targets cannot receive multi-word arguments through a plain `spawn`, so the
wrapper delegates through a temporary `.bat` file (`cmd /c`), written as
UTF-8 with a `chcp 65001` preamble — arguments with spaces, quotes and
non-ASCII characters survive intact, and the exit code propagates.

## Environment variables

| Variable | Effect |
|----------|--------|
| `APEX_BINARY` | Run this executable instead of resolving (e.g. a source checkout `bin/apex`). |
| `APEX_VERSION` | Pin the release version installed on first run (e.g. `0.1.0`). |
| `APEX_INSTALL_METHOD` | `auto` (default) or `native`. Any other value is rejected. |
| `APEX_NATIVE` | `0` = never download the native backend. |
| `APEX_INSTALL_DIR` | Native install directory (default `~/.apex/bin`). |
| `APEX_TUI_DIR` | TUI install directory (default `~/.apex/tui-frontend`). |
| `APEX_TUI_URL` | TUI source archive URL (default: GitHub `dev` branch zip). |
| `APEX_HTTP_PORT` | Port for the native backend when launching the TUI (default `8765`). |
| `APEX_SKIP_INSTALL` | `1` = fail fast with a hint instead of auto-installing. |

## Troubleshooting

- **Native download fails** — check `APEX_INSTALL_DIR` is writable and that
  the release publishes the asset for your target; the checksum sidecar must
  match the archive.
- **TUI download fails** — check `APEX_TUI_DIR` is writable and that
  `APEX_TUI_URL` points to a valid archive containing a `tui-frontend/`
  directory; bun or npm must be on PATH to install TUI dependencies.
- **Wrapper picks the wrong apex** — set `APEX_BINARY=/path/to/apex`.
- **`APEX_INSTALL_METHOD=pipx` fails** — the pip, pipx and uv channels were
  removed. Unset the variable (or set it to `native`).
- **Skip provisioning** — set `APEX_SKIP_INSTALL=1` to avoid downloading
  anything at install time.

## Development

```bash
cd integrations/npm
npm test            # node --test (no dependencies required)
```

Publishing happens from the `Release` workflow on `v*` tags and requires the
`NPM_TOKEN` repository secret. The release job fails when the package
version does not match the tag.
