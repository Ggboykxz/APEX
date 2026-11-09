# Installation

APEX has one canonical release (`VERSION` at the repository root) and two
supported distribution channels:

- the **npm wrapper** (`apex-ai`), which provides the `apex` command and
  downloads the verified native backend on first run;
- the **native Rust backend** (`apex-rs`), a headless binary published as a
  GitHub Release asset for five targets.

PyPI, pip, pipx and uv are **not** installation channels. The Python CLI/TUI
still exists and can be run from a source checkout for development, but it is
not distributed.

| Channel | What you get | Best for |
|---|---|---|
| `npm install -g apex-ai` | `apex` command + native backend | Node users |
| `install.sh` / `install.ps1` | npm, native or Docker install | Scripted setup |
| Native release asset | `apex-rs` (headless: serve/run/tools) | No Node, servers |
| Docker | APEX in a container | CI, reproducible envs |
| Source checkout | Full Python CLI/TUI | Development |

## Requirements

- **npm channel**: Node 16 or newer.
- **Native backend**: no runtime dependency; the release asset is a static
  binary for your platform.
- **Docker channel**: Docker Engine or Docker Desktop.

## Install via npm (recommended)

```bash
npm install -g apex-ai
apex --version
apex run "Fix the bug"
apex serve --port 8765
```

The wrapper resolves `APEX_BINARY`, then an `apex` executable on `PATH`, then
`apex-rs` (on `PATH` or in `~/.apex/bin`). If nothing is found it downloads
the matching release asset, verifies its `.sha256` sidecar and installs
`apex-rs` into `~/.apex/bin` (`APEX_INSTALL_DIR` overrides). No Node
dependency is installed at runtime.

## Native backend (headless)

The Rust backend serves the same HTTP API and tool registry but has no TUI.
It is installed as `apex-rs` (or `apex-rs.exe`) — never as `apex` — so it can
never shadow an `apex` launcher.

```bash
# Installer
bash install.sh --method native --version 0.1.0

# Managed path
~/.apex/bin/apex-rs serve --port 8765
```

Five targets are published with each release:

| Platform | Asset |
|---|---|
| Linux x86_64 | `apex-rs-x86_64-unknown-linux-gnu.tar.gz` |
| Linux aarch64 | `apex-rs-aarch64-unknown-linux-gnu.tar.gz` |
| macOS x86_64 | `apex-rs-x86_64-apple-darwin.tar.gz` |
| macOS aarch64 | `apex-rs-aarch64-apple-darwin.tar.gz` |
| Windows x86_64 | `apex-rs-x86_64-pc-windows-msvc.zip` |

Every archive has a `.sha256` sidecar. The installer and the npm wrapper
verify the digest **before** writing anything; a mismatch aborts. No crates.io
publication exists for `apex-rs` (see
[ADR-0008](../adr/ADR-0008-installation-refonte.md) and
[ADR-0009](../adr/ADR-0009-npm-native-only.md)).

## Unified installers

`scripts/install.sh` (macOS, Linux) and `scripts/install.ps1` (Windows)
accept the same options:

| Option | Effect |
|---|---|
| `--method auto` | Default: native download |
| `--method npm` | `npm install -g apex-ai` (requires Node) |
| `--method native` | Download and verify the Rust backend |
| `--method docker` | Write a Docker-based `apex` launcher |
| `--version X.Y.Z` | Pin a release (default: latest) |
| `--prefix DIR` | Install dir for native/docker (default `~/.apex/bin`) |
| `--no-path` | Never edit the shell profile / user PATH |
| `--yes` | Do not ask for confirmation |
| `--dry-run` | Print every action without changing anything |
| `--uninstall` | Uninstall APEX |
| `--purge` | With `--uninstall`: also remove credentials and config |

```bash
# macOS / Linux
curl -fsSLO https://apex-ai.dev/install.sh
bash install.sh --method npm --yes

# Windows (PowerShell)
Invoke-WebRequest https://apex-ai.dev/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Method native -Yes
```

The installers never install anything on `--dry-run`. The repository-root
`install.sh` / `install.ps1` only dispatch to these canonical scripts.

## Docker

```bash
docker pull ghcr.io/ggboykxz/apex:latest
docker run -it --rm -v "$(pwd):/workspace" -w /workspace \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  ghcr.io/ggboykxz/apex
```

`install.sh --method docker` (or `-Method docker` on Windows) writes a small
`apex` launcher that runs the image with your current directory mounted and
the usual provider keys forwarded.

## From source (development)

The Python CLI/TUI is not distributed through a package index. Run it from a
checkout (this is a development workflow, not an installation channel):

```bash
git clone https://github.com/Ggboykxz/APEX.git
cd APEX
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Verify

```bash
apex --version        # npm channel
apex-rs --version     # native channel
```

The printed version must match `VERSION` and the release tag. In CI,
`python scripts/version.py check` enforces that every manifest agrees.

## Upgrade

```bash
apex upgrade --method npm        # npm install -g apex-ai@<latest>
apex upgrade --method native     # verified native download
apex upgrade --check             # compare the installed version with GitHub
```

`apex upgrade` uses the channel that installed the running copy. A source
checkout has no package-manager channel: update it with `git pull` and
reinstall the dev dependencies. `pip`, `pipx` and `uv` are rejected.

## Uninstall

```bash
apex uninstall               # native binary, sessions, memory, tasks, config
apex uninstall --dry-run     # list what would be removed
apex uninstall --keep-config # keep ~/.config/apex
apex uninstall --keep-data   # keep sessions/memory/tasks
apex uninstall --purge       # also remove api_keys.json and gateway.json
```

The standalone installers expose the same operation:

```bash
bash install.sh --uninstall [--purge]
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Uninstall [-Purge]
```

By default **credentials are never deleted**: `~/.apex/api_keys.json` and
`~/.apex/gateway.json` survive an uninstall. Only `--purge` removes the whole
`~/.apex` tree.

## Troubleshooting

- **`apex: command not found`** — the npm global bin directory (or
  `~/.apex/bin` for the native installer) is not on `PATH`. Re-run the
  installer without `--no-path`, or add it manually.
- **A version mismatch** — run `python scripts/version.py check` in a checkout
  to see which manifest drifted; `sync` rewrites them from `VERSION`.
- **Native download fails** — confirm the release publishes the asset for
  your target and that `APEX_INSTALL_DIR` is writable. Checksum mismatches
  are reported before anything is written.
- **Wrong `apex` is picked up** — set `APEX_BINARY=/path/to/apex`.
- **`APEX_INSTALL_METHOD=pipx` fails** — pip/pipx/uv channels were removed;
  unset the variable or set it to `native`.

See [Troubleshooting](../troubleshooting.md) for runtime issues.
