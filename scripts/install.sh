#!/usr/bin/env bash
set -euo pipefail

APEX_VERSION="${APEX_VERSION:-latest}"
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
cat << 'EOF'
    ___    ____  _______  __
   /   |  / __ \/ ____/ |/ /
  / /| | / /_/ / __/  |   /
 / ___ |/ ____/ /___ /   |
/_/  |_/_/   /_____//_/|_|
EOF
echo -e "${NC}Installing APEX — the universal AI coding agent${NC}\n"

if [ "$(uname -s)" = "Windows_NT" ]; then
    echo -e "${YELLOW}⚠️ For Windows, use PowerShell instead:${NC}"
    echo "  irm https://apex-agent.dev/install.ps1 | iex"
    exit 1
fi

OS="$(uname -s)"
ARCH="$(uname -m)"
echo -e "${CYAN}Detected: ${OS} ${ARCH}${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python 3.11+ required. Install from https://python.org${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"; then
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}✗ Python 3.11+ required (found ${PYTHON_VERSION})${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Choose installation method:${NC}"
echo "  1) pipx (recommended - isolated)"
echo "  2) pip (user install)"
echo "  3) pip (system-wide, requires sudo)"
echo ""
read -p "Enter choice [1]: " choice
choice="${choice:-1}"

case $choice in
    1)
        if command -v pipx &>/dev/null; then
            echo -e "${CYAN}→ Installing with pipx...${NC}"
            pipx install apex-agent
        else
            echo -e "${YELLOW}pipx not found. Installing...${NC}"
            pip3 install pipx
            pipx install apex-agent
        fi
        ;;
    2)
        echo -e "${CYAN}→ Installing with pip (user)...${NC}"
        pip3 install --user apex-agent
        ;;
    3)
        echo -e "${CYAN}→ Installing with pip (system-wide)...${NC}"
        sudo pip3 install apex-agent
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✓ APEX installed successfully!${NC}"
echo ""
echo -e "  ${CYAN}Get started:${NC}  apex"
echo -e "  ${CYAN}Set API key:${NC}  export ANTHROPIC_API_KEY=sk-ant-..."
echo -e "  ${CYAN}Docs:${NC}         https://apex-agent.dev/docs"
echo ""
echo -e "${YELLOW}Quick start:${NC}"
echo "  apex                    # Interactive mode"
echo "  apex 'fix my code'      # One-shot mode"
echo "  apex --list-models      # See all models"
echo ""