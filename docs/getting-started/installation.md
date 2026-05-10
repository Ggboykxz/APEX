# Installation

APEX can be installed through several methods depending on your platform and preferences. The quickest way to get started is via `pip`, which pulls the latest stable release from PyPI. If you prefer isolated environments, `pipx` is the recommended approach since it installs APEX into its own virtual environment without polluting your global Python packages.

## Install with pip

```bash
pip install apex-ai
```

## Install with pipx (recommended)

```bash
pipx install apex-ai
```

## Install with Homebrew (macOS & Linux)

```bash
brew tap apex-ai/tap
brew install apex
```

## Install with Docker

APEX ships an official Docker image for containerized usage. This is ideal for CI/CD pipelines or when you want a fully reproducible environment without installing Python dependencies on the host.

```bash
docker pull ghcr.io/apex-ai/apex:latest
docker run -it --rm -e OPENAI_API_KEY=$OPENAI_API_KEY ghcr.io/apex-ai/apex
```

## Install from Source

Cloning from source gives you access to the latest development branch and is required if you plan to contribute. Make sure you have Python 3.10+ and Git installed.

```bash
git clone https://github.com/apex-ai/apex.git
cd apex
pip install -e ".[dev]"
```

After installation, verify everything works by running `apex --version`. You should see the current version printed along with the detected Python interpreter path. If you encounter any issues, refer to the [Troubleshooting](../troubleshooting.md) page or open an issue on GitHub.
