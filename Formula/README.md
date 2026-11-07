# Homebrew formula

`Formula/apex-ai.rb.tmpl` is the source of truth. `Formula/apex-ai.rb` is
**generated at release time** by `scripts/render_homebrew.py`, because the
formula needs the SHA256 of the PyPI sdist and that digest only exists once
the release build has produced it.

The rendered formula is attached to every GitHub release as `apex-ai.rb`.

## Install

```bash
# From the current release asset
curl -fsSLO https://github.com/Ggboykxz/APEX/releases/latest/download/apex-ai.rb
brew install --formula ./apex-ai.rb

# Or from a tap, if you maintain one with the rendered file
brew install <tap>/apex-ai
```

The formula installs the Python CLI/TUI (Python 3.12) — the same package as
`pip install apex-ai`. The native Rust backend (`apex-rs`) is not installed
by Homebrew; use `scripts/install.sh --method native` or the npm wrapper with
`APEX_INSTALL_METHOD=native`.

## Regenerate by hand

```bash
VERSION="$(cat VERSION)"
URL="https://files.pythonhosted.org/packages/source/a/apex-ai/apex_ai-${VERSION}.tar.gz"
SHA="$(curl -fsSL "$URL" | sha256sum | cut -d' ' -f1)"
python scripts/render_homebrew.py --version "$VERSION" --sha256 "$SHA" --url "$URL"
```

Only commit the template, never the rendered file: a committed formula would
point at a digest that no longer matches the next release.
