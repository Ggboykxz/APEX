# Installation

APEX is distributed through **npm** (the `apex-ai` wrapper, which provides the
`apex` command) and the **native Rust backend** (`apex-rs`, headless) published
as GitHub Release assets. PyPI, pip, pipx and uv are not installation
channels; the Python CLI/TUI is only available from a source checkout.

See the [full installation matrix](getting-started/installation.md) for every
option.

## Requirements

- Node 16+ for the npm channel.
- No runtime dependency for the native backend.
- API keys for your chosen model(s).

## Install via npm (recommended)

```bash
npm install -g apex-ai
```

The wrapper downloads the verified `apex-rs` release asset on first run and
then delegates every command to it.

## Install the native backend

```bash
bash install.sh --method native
~/.apex/bin/apex-rs --version
```

The binary is installed as `apex-rs` (never `apex`) and verified against the
`.sha256` sidecar published with the release.

## Install with Docker

APEX ships an official Docker image for containerized usage. This is ideal for CI/CD pipelines or when you want a fully reproducible environment without installing anything on the host.

```bash
docker pull ghcr.io/ggboykxz/apex:latest
docker run -it --rm -v $(pwd):/workspace -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY ghcr.io/ggboykxz/apex
```

## Install from source (development)

The Python CLI/TUI is not packaged for distribution. Run it from a checkout:

```bash
git clone https://github.com/Ggboykxz/APEX.git
cd APEX
pip install -e .            # development only
# or with dev dependencies
pip install -e ".[dev]"
```

## Verify installation

```bash
apex --version        # npm channel
apex-rs --version     # native channel
apex models           # List available models (subcommand)
apex --list-models    # Same thing (flag)
```

## API Keys

APEX requires API keys for the models you want to use. Set them in:

1. `~/.apex/.env`
2. `./.env` (project root)
3. `~/.env`

Example `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...
DEEPSEEK_API_KEY=...
GEMINI_API_KEY=...
COHERE_API_KEY=...
```

For local models (Ollama), no API key needed.

## TUI Setup

The TUI is part of the Python CLI/TUI, which runs from a source checkout. The
backend starts on a random localhost port and the Ink frontend connects via
WebSocket EventBus for real-time synchronization.

```bash
# From a checkout (with dev dependencies installed)
apex

# Or explicitly
apex tui
```

The backend port is written to `~/.apex/state/` for discovery.

## Upgrade

```bash
apex upgrade --method npm      # npm install -g apex-ai@<latest>
apex upgrade --method native   # verified native download
apex upgrade --check           # compare with the latest GitHub release
```

A source checkout is updated with `git pull`; pip/pipx/uv are no longer
upgrade channels.
