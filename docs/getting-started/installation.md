# Installation

APEX has one canonical release (`VERSION` at the repository root) and several
supported installation channels. The default experience is the **Python
CLI/TUI**, which ships every feature (agents, TUI, gateway, sharing). The
**native backend** (`apex-rs`, written in Rust) is headless and opt-in.

| Channel | What you get | Best for |
|---|---|---|
| `pipx` (recommended) | Full CLI/TUI | Isolated installs |
| `uv` | Full CLI/TUI | Fast, isolated installs |
| `pip` | Full CLI/TUI | Existing virtualenvs |
| `npm` (`apex-ai`) | Full CLI/TUI (provisions Python), or native | Node users |
| `install.sh` / `install.ps1` | Any channel, unified flags | Scripted setup |
| Docker | Full CLI/TUI in a container | CI, reproducible envs |
| Homebrew | Full CLI/TUI | macOS/Linuxbrew users |
| GitHub release assets | Native backend (headless) | No Python, servers |

## Requirements

- **Python channel**: Python 3.11 or newer.
- **Native backend**: no runtime dependency; the release asset is a static
  binary for your platform.
- **npm wrapper**: Node 16+ for the wrapper itself; Python 3.11+ unless you
  choose the native backend.
- **Docker channel**: Docker Engine or Docker Desktop.

## Install the Python CLI/TUI

```bash
# pipx — recommended (isolated, no global pollution)
pipx install apex-ai

# uv — fastest
uv tool install apex-ai

# pip — inside an existing virtualenv
pip install apex-ai

# npm — zero-dependency wrapper, provisions Python on first run
npm install -g apex-ai
```

After installation:

```bash
apex              # TUI (default)
apex -p "Fix the bug"    # one-shot
apex --version
```

## Unified installers

`scripts/install.sh` (macOS, Linux) and `scripts/install.ps1` (Windows)
accept the same options:

| Option | Effect |
|---|---|
| `--method auto` | Default: `pipx` > `uv` > `pip`, else native fallback |
| `--method python` | Alias for `auto` |
| `--method pipx` | Force pipx |
| `--method uv` | Force uv |
| `--method pip` | Force `python -m pip --user` |
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
bash install.sh --method uv --yes

# Windows (PowerShell)
Invoke-WebRequest https://apex-ai.dev/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Method pipx -Yes
```

The installers never run a silent `curl | sh` bootstrap and never install
anything on `--dry-run`.

## Native backend (opt-in, headless)

The Rust backend serves the same HTTP API and tool registry but has no TUI.
It is installed as `apex-rs` (or `apex-rs.exe`) — never as `apex`, so it can
never shadow the Python CLI.

```bash
# Installer
bash install.sh --method native --version 2.5.0

# npm wrapper
APEX_INSTALL_METHOD=native npm exec -- apex serve

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
publication exists for `apex-rs` (see [ADR-0008](../adr/ADR-0008-installation-refonte.md)).

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

## Homebrew

The release publishes a rendered formula (`apex-ai.rb`) alongside the other
assets:

```bash
curl -fsSLO https://github.com/Ggboykxz/APEX/releases/latest/download/apex-ai.rb
brew install --formula ./apex-ai.rb
```

The formula installs the Python CLI/TUI with Python 3.12. It is rendered at
release time because it embeds the SHA256 of the PyPI sdist; see
[`Formula/README.md`](https://github.com/Ggboykxz/APEX/blob/dev/Formula/README.md).

## From source

```bash
git clone https://github.com/Ggboykxz/APEX.git
cd APEX
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Verify

```bash
apex --version
apex models
```

The printed version must match `VERSION` and the release tag. In CI,
`python scripts/version.py check` enforces that every manifest agrees.

## Upgrade

```bash
apex upgrade                 # detect pipx/uv/pip/npm/native and upgrade
apex upgrade --check         # compare the installed version with GitHub
apex upgrade --method uv     # force a channel
APEX_VERSION=2.5.0 apex upgrade
```

`apex upgrade` uses the channel that installed the running copy, so a pipx
install is not silently overwritten by pip.

## Uninstall

```bash
apex uninstall               # package, native binary, sessions, memory, tasks, config
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

- **`apex: command not found`** — the install directory is not on `PATH`.
  Re-run the installer without `--no-path`, or add `~/.apex/bin` (or your
  pipx/uv bin directory) manually.
- **A version mismatch** — run `python scripts/version.py check` in a checkout
  to see which manifest drifted; `sync` rewrites them from `VERSION`.
- **Native download fails** — confirm the release publishes the asset for
  your target and that `APEX_INSTALL_DIR` is writable. Checksum mismatches
  are reported before anything is written.
- **Wrong `apex` is picked up** — set `APEX_BINARY=/path/to/apex`.

See [Troubleshooting](../troubleshooting.md) for runtime issues.
