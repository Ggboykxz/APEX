#!/usr/bin/env bash
# ============================================
# APEX installer entry point — https://github.com/Ggboykxz/APEX
#
# This file only dispatches to the canonical installer, `scripts/install.sh`,
# so the one-liner documented on the website keeps working:
#
#   curl -fsSLO https://raw.githubusercontent.com/Ggboykxz/APEX/main/install.sh
#   bash install.sh [--method auto|npm|native|docker] [...]
#
# APEX ships through npm and the native Rust backend only; PyPI/pip/pipx/uv
# channels were removed.
# ============================================
set -euo pipefail

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    echo "curl or wget is required to fetch the installer" >&2
    exit 1
fi

here=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -n "$here" ] && [ -f "$here/scripts/install.sh" ]; then
    exec bash "$here/scripts/install.sh" "$@"
fi

REF="${APEX_REF:-main}"
URL="https://raw.githubusercontent.com/Ggboykxz/APEX/${REF}/scripts/install.sh"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

if command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 3 -o "$tmp" "$URL"
else
    wget -q -O "$tmp" "$URL"
fi

exec bash "$tmp" "$@"
