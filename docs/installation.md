# Installation

## Requirements

- Python 3.11+
- API keys for your chosen model(s)

## Install via pip

```bash
pip install apex-ai
```

## Install via pipx (recommended)

```bash
pipx install apex-ai
```

## Install via uv (fastest)

```bash
uv tool install apex-ai
```

## Install with Docker

APEX ships an official Docker image for containerized usage. This is ideal for CI/CD pipelines or when you want a fully reproducible environment without installing Python dependencies on the host.

```bash
docker pull ghcr.io/ggboykxz/apex:latest
docker run -it --rm -v $(pwd):/workspace -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY ghcr.io/ggboykxz/apex
```

## Install from source

```bash
git clone https://github.com/Ggboykxz/APEX.git
cd APEX
pip install -e .
# or with dev dependencies
pip install -e ".[dev]"
```

## Verify installation

```bash
apex --version
apex models          # List available models (subcommand)
apex --list-models   # Same thing (flag)
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

After installing apex-ai via pip, you need to set up the TUI frontend:

```bash
# One-time TUI setup (installs Bun + downloads tui-frontend)
apex install-tui

# Then launch TUI
apex tui
```

For dev/git users, the TUI works directly: `apex tui` (auto-installs deps on first run).

## Upgrade

```bash
pip install --upgrade apex-ai
```
