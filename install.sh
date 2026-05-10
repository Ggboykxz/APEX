#!/usr/bin/env bash
set -euo pipefail

# ============================================
# APEX Installer — The universal AI coding agent
# https://github.com/Ggboykxz/APEX
# ============================================

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MUTED='\033[2m'
NC='\033[0m'

version=""
uninstall_mode=false
default_model=""
install_method=""

usage() {
    cat <<EOF
${CYAN}◆ APEX Installer${NC}

The universal AI coding agent. Every model. One terminal.

${GREEN}Usage:${NC}
    curl -fsSL https://apex-agent.dev/install.sh | bash
    ./install.sh [options]

${GREEN}Options:${NC}
    -h, --help              Display this help message
    -v, --version <ver>     Install a specific version
    -u, --uninstall         Remove APEX
    -m, --model <model>     Set default model
    -m, --method <method>   Force install method (uv, pipx, pip, docker)

${GREEN}Examples:${NC}
    ./install.sh --version 1.3.0
    ./install.sh --model claude-sonnet
    ./install.sh --method uv

${GREEN}Requirements:${NC}
    - Python 3.11+
    - pip, pipx, or uv

EOF
}

uninstall() {
    echo -e "${MUTED}Removing APEX...${NC}"
    rm -f "$HOME/.local/bin/apex"
    # Also remove pipx/pip installs
    command -v pipx &>/dev/null && pipx uninstall apex-agent 2>/dev/null || true
    command -v pip3 &>/dev/null && pip3 uninstall -y apex-agent 2>/dev/null || true
    command -v uv &>/dev/null && uv tool uninstall apex-agent 2>/dev/null || true
    echo -e "${GREEN}APEX removed successfully!${NC}"
}

install_with_uv() {
    if command -v uv &>/dev/null; then
        echo -e "${MUTED}Installing with uv (fastest)...${NC}"
        if [ -n "$version" ]; then
            uv tool install apex-agent=="$version"
        else
            uv tool install apex-agent
        fi
        return 0
    fi
    return 1
}

install_with_pipx() {
    if command -v pipx &>/dev/null; then
        echo -e "${MUTED}Installing with pipx...${NC}"
        if [ -n "$version" ]; then
            pipx install apex-agent=="$version"
        else
            pipx install apex-agent
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
        $pip_cmd install apex-agent=="$version" --break-system-packages 2>/dev/null || \
        $pip_cmd install apex-agent=="$version" --user 2>/dev/null
    else
        $pip_cmd install apex-agent --break-system-packages 2>/dev/null || \
        $pip_cmd install apex-agent --user 2>/dev/null
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
    echo -e "${CYAN}  ▲ APEX${NC}"
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
        echo "  pip install apex-agent"
        echo "  pipx install apex-agent"
        echo "  uv tool install apex-agent"
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
    echo -e "${GREEN}APEX installed successfully!${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} Set your API key:"
    echo -e "     export ANTHROPIC_API_KEY=sk-ant-..."
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
