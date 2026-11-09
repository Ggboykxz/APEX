#!/usr/bin/env bash
# ============================================
# APEX installer — https://github.com/Ggboykxz/APEX
#
# APEX ships through two channels: the npm wrapper (`apex`) and the native
# Rust backend (`apex-rs`, headless). PyPI/pip/pipx/uv no longer exist.
#
# Usage:
#   curl -fsSLO https://apex-ai.dev/install.sh
#   bash install.sh [options]
#
# Options:
#   --method METHOD   auto | npm | native | docker
#                     (default: auto — native download)
#   --version VER     pin a release (default: latest)
#   --prefix DIR      install dir for native/docker (default: ~/.apex/bin)
#   --no-path         never edit your shell profile
#   --yes             do not ask for confirmation
#   --dry-run         print actions without changing anything
#   --uninstall       uninstall APEX
#   --purge           with --uninstall: also remove credentials and config
#   -h, --help        show this help
#
# Environment: APEX_METHOD, APEX_VERSION, APEX_INSTALL_DIR, APEX_IMAGE
# ============================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MUTED='\033[2m'
NC='\033[0m'

REPO="Ggboykxz/APEX"
PACKAGE="apex-ai"
IMAGE="${APEX_IMAGE:-ghcr.io/ggboykxz/apex}"
PROFILE_BEGIN="# >>> apex installer >>>"
PROFILE_END="# <<< apex installer <<<"

METHOD="${APEX_METHOD:-auto}"
VERSION="${APEX_VERSION:-latest}"
PREFIX="${APEX_INSTALL_DIR:-$HOME/.apex/bin}"
NO_PATH=0
ASSUME_YES=0
DRY_RUN=0
UNINSTALL=0
PURGE=0

say() { printf '%b\n' "$1"; }
info() { say "${CYAN}$1${NC}"; }
ok() { say "${GREEN}$1${NC}"; }
warn() { say "${YELLOW}$1${NC}"; }
die() {
    say "${RED}$1${NC}" >&2
    exit 1
}

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        say "${MUTED}  would run: $*${NC}"
        return 0
    fi
    "$@"
}

usage() {
    sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --method) METHOD="${2:-}"; shift 2 ;;
        --method=*) METHOD="${1#*=}"; shift ;;
        --version) VERSION="${2:-}"; shift 2 ;;
        --version=*) VERSION="${1#*=}"; shift ;;
        --prefix) PREFIX="${2:-}"; shift 2 ;;
        --prefix=*) PREFIX="${1#*=}"; shift ;;
        --no-path) NO_PATH=1; shift ;;
        --yes|-y) ASSUME_YES=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        --uninstall) UNINSTALL=1; shift ;;
        --purge) PURGE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1 (try --help)" ;;
    esac
done

case "$METHOD" in
    auto|npm|native|docker) ;;
    *) die "Unknown method '$METHOD' (auto|npm|native|docker)" ;;
esac
case "$PREFIX" in
    "~"*) PREFIX="$HOME${PREFIX#\~}" ;;
esac
case "$VERSION" in
    v*) VERSION="${VERSION#v}" ;;
esac
[ -n "$VERSION" ] || VERSION="latest"

say ""
say "${CYAN}  ▲ APEX${NC}"
say "${MUTED}  The universal AI coding agent. Every model. One terminal.${NC}"
say ""

OS_RAW="$(uname -s)"
ARCH_RAW="$(uname -m)"
case "$OS_RAW" in
    Linux) OS="linux" ;;
    Darwin) OS="darwin" ;;
    MINGW*|MSYS*|CYGWIN*) die "On Windows use install.ps1 instead: irm https://apex-ai.dev/install.ps1 | iex" ;;
    *) die "Unsupported platform: $OS_RAW" ;;
esac
case "$ARCH_RAW" in
    x86_64|amd64) ARCH="x86_64" ;;
    arm64|aarch64) ARCH="aarch64" ;;
    *) die "Unsupported architecture: $ARCH_RAW" ;;
esac
info "Detected: $OS $ARCH"

have() { command -v "$1" >/dev/null 2>&1; }

confirm() {
    [ "$ASSUME_YES" -eq 1 ] && return 0
    [ "$DRY_RUN" -eq 1 ] && return 0
    if [ ! -t 0 ]; then
        return 0
    fi
    printf '%b' "${YELLOW}$1 [y/N] ${NC}"
    read -r reply
    case "$reply" in
        y|Y|yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

download() {
    local url="$1" out="$2"
    if [ "$DRY_RUN" -eq 1 ]; then
        say "${MUTED}  would download: $url${NC}"
        return 0
    fi
    if have curl; then
        curl -fsSL --retry 3 -o "$out" "$url"
    elif have wget; then
        wget -q -O "$out" "$url"
    else
        die "curl or wget is required to download the native backend"
    fi
}

sha256_of() {
    if have sha256sum; then
        sha256sum "$1" | awk '{print $1}'
    elif have shasum; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        die "sha256sum or shasum is required to verify the download"
    fi
}

add_to_path() {
    local dir="$1"
    [ "$NO_PATH" -eq 1 ] && { warn "Skipping PATH update (--no-path)."; return 0; }
    case ":$PATH:" in
        *":$dir:"*) ok "PATH already contains $dir"; return 0 ;;
    esac

    local profile=""
    for candidate in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile"; do
        if [ -f "$candidate" ]; then profile="$candidate"; break; fi
    done
    if [ -z "$profile" ]; then
        profile="$HOME/.profile"
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        say "${MUTED}  would add $dir to PATH in $profile${NC}"
        return 0
    fi
    if [ -f "$profile" ] && grep -qF "$PROFILE_BEGIN" "$profile"; then
        ok "PATH block already present in $profile"
        return 0
    fi
    {
        printf '\n%s\n' "$PROFILE_BEGIN"
        printf 'export PATH="%s:$PATH"\n' "$dir"
        printf '%s\n' "$PROFILE_END"
    } >>"$profile"
    ok "Added $dir to PATH in $profile (open a new shell)"
}

# ── Uninstall ───────────────────────────────────────────────────────────────

remove_path() {
    local target="$1"
    if [ -e "$target" ] || [ -L "$target" ]; then
        run rm -rf "$target"
        ok "Removed $target"
    fi
}

remove_path_block() {
    local profile="$1"
    [ -f "$profile" ] || return 0
    grep -qF "$PROFILE_BEGIN" "$profile" || return 0
    if [ "$DRY_RUN" -eq 1 ]; then
        say "${MUTED}  would remove the PATH block from $profile${NC}"
        return 0
    fi
    local tmp
    tmp="$(mktemp)"
    awk -v begin="$PROFILE_BEGIN" -v end="$PROFILE_END" '
        $0 == begin { skip = 1; next }
        $0 == end { skip = 0; next }
        !skip { print }
    ' "$profile" >"$tmp"
    mv "$tmp" "$profile"
    ok "Removed the PATH block from $profile"
}

uninstall_apex() {
    info "Uninstalling APEX${PURGE:+ (purge)}…"
    if ! confirm "Remove APEX from this machine?"; then
        warn "Cancelled."
        exit 0
    fi

    remove_path "$PREFIX/apex-rs"
    remove_path "$PREFIX/apex"
    if [ -d "$PREFIX" ] && [ -z "$(ls -A "$PREFIX" 2>/dev/null)" ]; then
        run rmdir "$PREFIX" || true
    fi

    if have npm; then run npm uninstall -g "$PACKAGE" || true; fi

    remove_path "$HOME/.config/apex"
    remove_path "$HOME/.apex/sessions"
    remove_path "$HOME/.apex/memory"
    remove_path "$HOME/.apex/tasks"

    for profile in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile"; do
        remove_path_block "$profile"
    done

    if [ "$PURGE" -eq 1 ]; then
        remove_path "$HOME/.apex"
    else
        say "${MUTED}Kept: $HOME/.apex/api_keys.json, $HOME/.apex/gateway.json (use --purge to remove)${NC}"
    fi
    ok "APEX uninstalled."
}

# ── Install methods ─────────────────────────────────────────────────────────

install_npm() {
    have npm || die "npm is not installed (https://nodejs.org)"
    local spec="$PACKAGE"
    [ "$VERSION" = "latest" ] || spec="$PACKAGE@$VERSION"

    info "Installing $spec globally with npm…"
    say "${MUTED}The npm wrapper downloads the verified apex-rs backend on first run.${NC}"
    if ! confirm "Install APEX via npm?"; then
        warn "Cancelled."
        exit 0
    fi
    run npm install -g "$spec"
    ok "APEX installed."
    say "${MUTED}Run: apex${NC}"
}

native_asset() {
    case "$OS" in
        linux) echo "apex-rs-${ARCH}-unknown-linux-gnu.tar.gz" ;;
        darwin) echo "apex-rs-${ARCH}-apple-darwin.tar.gz" ;;
    esac
}

install_native() {
    local asset base tmp expected actual archive binary
    asset="$(native_asset)"
    if [ "$VERSION" = "latest" ]; then
        base="https://github.com/$REPO/releases/latest/download"
    else
        base="https://github.com/$REPO/releases/download/v$VERSION"
    fi

    info "Installing the native backend ($asset)…"
    say "${MUTED}The native backend is headless (serve, run, tools). Install via npm for an 'apex' command.${NC}"
    if ! confirm "Download the native backend from GitHub?"; then
        warn "Cancelled."
        exit 0
    fi

    tmp="$(mktemp -d)"
    trap "rm -rf '$tmp'" EXIT
    download "$base/$asset" "$tmp/$asset"
    download "$base/$asset.sha256" "$tmp/$asset.sha256"

    if [ "$DRY_RUN" -eq 0 ]; then
        expected="$(awk '{print $1}' "$tmp/$asset.sha256" | head -n1)"
        actual="$(sha256_of "$tmp/$asset")"
        if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
            die "Checksum mismatch for $asset — refusing to install."
        fi
        ok "Checksum verified."

        case "$asset" in
            *.zip) unzip -q "$tmp/$asset" -d "$tmp/unpack" ;;
            *) tar -xzf "$tmp/$asset" -C "$tmp" ;;
        esac
        archive="$(find "$tmp" -type f -name apex-rs | head -n1)"
        [ -n "$archive" ] || die "The archive does not contain apex-rs"
        run mkdir -p "$PREFIX"
        run install -m 0755 "$archive" "$PREFIX/apex-rs"
    else
        say "${MUTED}  would verify the checksum and install apex-rs to $PREFIX${NC}"
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        say "${MUTED}  would install apex-rs to $PREFIX/apex-rs${NC}"
    else
        ok "Native backend installed at $PREFIX/apex-rs"
    fi
    add_to_path "$PREFIX"
}

install_docker() {
    have docker || die "docker is not installed"
    local tag="$VERSION"
    [ "$tag" = "latest" ] || tag="$tag"
    info "Creating the Docker launcher (image $IMAGE:$tag)…"
    if ! confirm "Install a Docker-based 'apex' launcher?"; then
        warn "Cancelled."
        exit 0
    fi
    run mkdir -p "$PREFIX"
    if [ "$DRY_RUN" -eq 1 ]; then
        say "${MUTED}  would write $PREFIX/apex${NC}"
    else
        ok "Docker launcher installed at $PREFIX/apex"
    fi
    add_to_path "$PREFIX"
}

# ── Main ────────────────────────────────────────────────────────────────────

if [ "$UNINSTALL" -eq 1 ]; then
    uninstall_apex
    exit 0
fi

if [ "$PURGE" -eq 1 ]; then
    die "--purge is only valid with --uninstall"
fi

case "$METHOD" in
    npm) install_npm ;;
    native|auto) install_native ;;
    docker) install_docker ;;
esac

say ""
ok "Done."
say "${MUTED}apex-rs --version  (npm: apex --version)${NC}"
