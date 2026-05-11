#!/usr/bin/env bash
set -euo pipefail

# ============================================
# APEX v1.2.0 Installer — The universal AI coding agent
# https://github.com/Ggboykxz/APEX
# ============================================

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MUTED='\033[0;90m'
BOLD='\033[1m'
NC='\033[0m'

APEX_VERSION="1.2.0"
version=""
uninstall_mode=false
default_model=""
install_method=""

usage() {
    cat <<EOF
${CYAN}${BOLD}◆ APEX Installer${NC}

The universal AI coding agent. Every model. One terminal.

${GREEN}Usage:${NC}
    curl -fsSL https://raw.githubusercontent.com/Ggboykxz/APEX/main/install.sh | bash
    ./install.sh [options]

${GREEN}Options:${NC}
    -h, --help              Display this help message
    -v, --version <ver>     Install a specific version
    -u, --uninstall         Remove APEX
    -m, --model <model>     Set default model
    --method <method>       Force install method (uv, pipx, pip, docker)

${GREEN}Examples:${NC}
    ./install.sh --version ${APEX_VERSION}
    ./install.sh --model claude-sonnet
    ./install.sh --method uv

${GREEN}Requirements:${NC}
    - Python 3.11+
    - pip, pipx, or uv

EOF
}

uninstall() {
    echo -e "${MUTED}Removing APEX...${NC}"
    rm -f "$HOME/.local/bin/apex" 2>/dev/null || true
    command -v pipx &>/dev/null && pipx uninstall apex-ai 2>/dev/null || true
    command -v pip3 &>/dev/null && pip3 uninstall -y apex-ai 2>/dev/null || true
    command -v uv &>/dev/null && uv tool uninstall apex-ai 2>/dev/null || true
    echo -e "${GREEN}APEX removed successfully!${NC}"
}

install_with_uv() {
    if command -v uv &>/dev/null; then
        echo -e "${MUTED}Installing with uv (fastest)...${NC}"
        if [ -n "$version" ]; then
            uv tool install "apex-ai==$version"
        else
            uv tool install apex-ai
        fi
        return 0
    fi
    return 1
}

install_with_pipx() {
    if command -v pipx &>/dev/null; then
        echo -e "${MUTED}Installing with pipx...${NC}"
        if [ -n "$version" ]; then
            pipx install "apex-ai==$version"
        else
            pipx install apex-ai
        fi
        return 0
    fi
    return 1
}

install_with_pip() {
    echo -e "${MUTED}Installing with pip...${NC}"
    local pip_cmd=""
    if command -v pip3 &>/dev/null; then
        pip_cmd="pip3"
    elif command -v pip &>/dev/null; then
        pip_cmd="pip"
    elif command -v python3 &>/dev/null; then
        pip_cmd="python3 -m pip"
    elif command -v python &>/dev/null; then
        pip_cmd="python -m pip"
    fi

    if [ -z "$pip_cmd" ]; then
        return 1
    fi

    if [ -n "$version" ]; then
        $pip_cmd install "apex-ai==$version" --break-system-packages 2>/dev/null || \
        $pip_cmd install "apex-ai==$version" --user 2>/dev/null
    else
        $pip_cmd install apex-ai --break-system-packages 2>/dev/null || \
        $pip_cmd install apex-ai --user 2>/dev/null
    fi
}

install_with_docker() {
    if command -v docker &>/dev/null; then
        echo -e "${MUTED}Pulling APEX Docker image...${NC}"
        docker pull ghcr.io/ggboykxz/apex:latest
        echo ""
        echo -e "${GREEN}Docker image pulled! Run with:${NC}"
        echo "  docker run -it -v \$(pwd):/workspace ghcr.io/ggboykxz/apex"
        return 0
    fi
    return 1
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)       usage; exit 0 ;;
            -v|--version)    version="$2"; shift 2 ;;
            -u|--uninstall)  uninstall_mode=true; shift ;;
            -m|--model)      default_model="$2"; shift 2 ;;
            --method)        install_method="$2"; shift 2 ;;
            *)               shift ;;
        esac
    done

    if $uninstall_mode; then
        uninstall
        exit 0
    fi

    echo ""
    echo -e "${CYAN}${BOLD}  ◆ APEX v${APEX_VERSION}${NC}"
    echo -e "${MUTED}  The universal AI coding agent. Every model. One terminal.${NC}"
    echo ""

    # Check Python version
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}Python 3.11+ required. Install from https://python.org${NC}"
        echo -e "${MUTED}Or use Docker: docker run -it ghcr.io/ggboykxz/apex${NC}"
        exit 1
    fi

    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"; then
        echo -e "${RED}Python 3.11+ required (found ${PY_VER})${NC}"
        exit 1
    fi
    echo -e "${GREEN}Python ${PY_VER} detected${NC}"
    echo ""

    # Install
    local success=false

    if [ -n "$install_method" ]; then
        case "$install_method" in
            uv)     install_with_uv && success=true ;;
            pipx)   install_with_pipx && success=true ;;
            pip)    install_with_pip && success=true ;;
            docker) install_with_docker && success=true ;;
            *)      echo -e "${RED}Unknown method: $install_method${NC}" ;;
        esac
    else
        install_with_uv && success=true || \
        install_with_pipx && success=true || \
        install_with_pip && success=true
    fi

    if ! $success; then
        echo ""
        echo -e "${RED}Installation failed!${NC}"
        echo -e "${MUTED}Try one of:${NC}"
        echo "  pip install apex-ai"
        echo "  pipx install apex-ai"
        echo "  uv tool install apex-ai"
        echo "  docker run -it ghcr.io/ggboykxz/apex"
        exit 1
    fi

    # Set default model if specified
    if [ -n "$default_model" ]; then
        mkdir -p "$HOME/.apex"
        echo "{\"model\": \"$default_model\"}" > "$HOME/.apex/config.json"
        echo -e "${MUTED}Default model set to: $default_model${NC}"
    fi

    echo ""
    echo -e "${GREEN}${BOLD}APEX v${APEX_VERSION} installed successfully!${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} Set your API key:"
    echo -e "     ${MUTED}export ANTHROPIC_API_KEY=sk-ant-...${NC}"
    echo ""
    echo -e "  ${CYAN}2.${NC} Launch APEX:"
    echo -e "     ${GREEN}apex${NC}"
    echo ""
    echo -e "  ${MUTED}Free models (no API key needed):${NC}"
    echo -e "     ${GREEN}apex --model ollama-llama3${NC}"
    echo ""
    echo -e "  ${MUTED}TUI mode:${NC}"
    echo -e "     ${GREEN}apex --tui${NC}"
    echo ""
    echo -e "  ${MUTED}Docker:${NC}"
    echo -e "     ${GREEN}docker run -it -v \$(pwd):/workspace ghcr.io/ggboykxz/apex${NC}"
    echo ""
}

main "$@"
