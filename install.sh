#!/usr/bin/env bash
set -euo pipefail
APP=apex

MUTED='\033[0;2m'
RED='\033[0;31m'
ORANGE='\033[38;5;214m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

usage() {
    cat <<EOF
${CYAN}◆ APEX Installer${NC}

The universal AI coding agent. Every model. One terminal.

${GREEN}Usage:${NC} install.sh [options]

${GREEN}Options:${NC}
    -h, --help              Display this help message
    -v, --version <ver>     Install a specific version
    -u, --uninstall         Remove APEX
    -m, --model <model>     Set default model

${GREEN}Examples:${NC}
    curl -fsSL https://apex-agent.dev/install.sh | bash
    ./install.sh --version 1.4.0
    ./install.sh --model claude-sonnet

${GREEN}Requirements:${NC}
    - Python 3.11+
    - pip or pipx

EOF
}

uninstall() {
    echo -e "${MUTED}Removing APEX...${NC}"
    rm -f "$HOME/.local/bin/apex"
    rm -f "$HOME/.local/bin/apex-tui"
    echo -e "${GREEN}APEX removed successfully!${NC}"
}

install_with_pipx() {
    if command -v pipx &> /dev/null; then
        echo -e "${MUTED}Installing with pipx...${NC}"
        pipx install apex-agent
        return 0
    fi
    return 1
}

install_with_pip() {
    echo -e "${MUTED}Installing with pip...${NC}"

    if command -v python3 &> /dev/null; then
        pip install apex-agent --break-system-packages 2>/dev/null && return 0
        pip install apex-agent --user 2>/dev/null && return 0
    fi

    if command -v python &> /dev/null; then
        python -m pip install apex-agent --break-system-packages 2>/dev/null && return 0
        python -m pip install apex-agent --user 2>/dev/null && return 0
    fi

    return 1
}

install_with_uv() {
    if command -v uv &> /dev/null; then
        echo -e "${MUTED}Installing with uv (fastest)...${NC}"
        uv tool install apex-agent
        return 0
    fi
    return 1
}

main() {
    local version=""
    local uninstall_mode=false
    local default_model=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--version)
                version="$2"
                shift 2
                ;;
            -u|--uninstall)
                uninstall_mode=true
                shift
                ;;
            -m|--model)
                default_model="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if $uninstall_mode; then
        uninstall
        exit 0
    fi

    echo ""
    echo -e "${CYAN}                   ▄     ${NC}"
    echo -e "${CYAN}█▀▀█ █▀▀█ █▀▀█ █▀▀▄ ${NC}█▀▀▀ █▀▀█ █▀▀█ █▀▀█"
    echo -e "${CYAN}█░░█ █░░█ █▀▀▀ █░░█ ${NC}█░░░ █░░█ █░░█ █▀▀▀"
    echo -e "${CYAN}▀▀▀▀ █▀▀▀ ▀▀▀▀ ▀  ▀ ${NC}▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀"
    echo ""
    echo -e "${MUTED}The universal AI coding agent. Every model. One terminal.${NC}"
    echo ""

    install_with_uv && {
        echo -e "${GREEN}✓ APEX installed successfully with uv!${NC}"
        echo ""
        echo -e "${MUTED}To get started:${NC}"
        echo ""
        echo -e "  ${CYAN}1.${NC} Set your API key:"
        echo -e "     export ${ORANGE}ANTHROPIC_API_KEY${NC}=sk-ant-..."
        echo ""
        echo -e "  ${CYAN}2.${NC} Launch APEX:"
        echo -e "     ${GREEN}apex${NC}"
        echo ""
        echo -e "  ${MUTED}For free models (no API key needed):${NC}"
        echo -e "     ${GREEN}apex --model ollama-llama3${NC}"
        echo ""
        return 0
    }

    install_with_pipx && {
        echo -e "${GREEN}✓ APEX installed successfully with pipx!${NC}"
        echo ""
        echo -e "${MUTED}To get started:${NC}"
        echo "  export ANTHROPIC_API_KEY=sk-ant-..."
        echo "  apex"
        echo ""
        return 0
    }

    install_with_pip && {
        echo -e "${GREEN}✓ APEX installed successfully!${NC}"
        echo ""
        echo -e "${MUTED}To get started:${NC}"
        echo "  export ANTHROPIC_API_KEY=sk-ant-..."
        echo "  apex"
        echo ""
        return 0
    }

    echo -e "${RED}✗ Failed to install APEX${NC}"
    echo -e "${MUTED}Please ensure Python 3.11+ is installed:${NC}"
    echo "  https://python.org"
    echo ""
    echo -e "${MUTED}Or try installing manually:${NC}"
    echo "  pip install apex-agent"
    echo ""
    exit 1
}

main "$@"
