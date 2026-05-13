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

APEX_VERSION="${APEX_VERSION:-latest}"

echo ""
echo -e "${CYAN}  ▲ APEX${NC}"
echo -e "${MUTED}  The universal AI coding agent. Every model. One terminal.${NC}"
echo ""

if [ "$(uname -s)" = "Windows_NT" ]; then
    echo -e "${YELLOW}For Windows, use PowerShell instead:${NC}"
    echo "  irm https://apex-ai.dev/install.ps1 | iex"
    exit 1
fi

OS="$(uname -s)"
ARCH="$(uname -m)"
echo -e "${CYAN}Detected: ${OS} ${ARCH}${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Python 3.11+ required. Install from https://python.org${NC}"
    echo -e "${MUTED}Or use Docker: docker run -it ghcr.io/ggboykxz/apex${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"; then
    echo -e "${GREEN}Python ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}Python 3.11+ required (found ${PYTHON_VERSION})${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Choose installation method:${NC}"
echo "  1) uv (recommended - fastest)"
echo "  2) pipx (isolated)"
echo "  3) pip (user install)"
echo "  4) Docker (containerized)"
echo ""
read -p "Enter choice [1]: " choice
choice="${choice:-1}"

case $choice in
    1)
        if command -v uv &>/dev/null; then
            echo -e "${CYAN}Installing with uv...${NC}"
            uv tool install apex-ai
        else
            echo -e "${YELLOW}uv not found. Installing...${NC}"
            curl -LsSf https://astral.sh/uv/install.sh | sh
            uv tool install apex-ai
        fi
        ;;
    2)
        if command -v pipx &>/dev/null; then
            echo -e "${CYAN}Installing with pipx...${NC}"
            pipx install apex-ai
        else
            echo -e "${YELLOW}pipx not found. Installing...${NC}"
            pip3 install pipx
            pipx install apex-ai
        fi
        ;;
    3)
        echo -e "${CYAN}Installing with pip (user)...${NC}"
        pip3 install --user apex-ai
        ;;
    4)
        echo -e "${CYAN}Pulling Docker image...${NC}"
        docker pull ghcr.io/ggboykxz/apex:latest
        echo ""
        echo -e "${GREEN}Run with:${NC}"
        echo "  docker run -it -v \$(pwd):/workspace ghcr.io/ggboykxz/apex"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}APEX installed successfully!${NC}"
echo ""
echo -e "  ${CYAN}Get started:${NC}  apex"
echo -e "  ${CYAN}Set API key:${NC}  export ANTHROPIC_API_KEY=sk-ant-..."
echo -e "  ${CYAN}TUI mode:${NC}     apex --tui"
echo -e "  ${CYAN}Docs:${NC}         https://apex-ai.dev/docs"
echo ""
