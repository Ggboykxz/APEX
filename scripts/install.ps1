$ErrorActionPreference = "Stop"

$CYAN = "`e[36m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$RED = "`e[31m"
$NC = "`e[0m"

Write-Host ""
Write-Host "$CYAN    ___    ____  _______  __$NC"
Write-Host "$CYAN   /   |  / __ \/ ____/ |/ /$NC"
Write-Host "$CYAN  / /| | / /_/ / __/  |   /$NC"
Write-Host "$CYAN / ___ |/ ____/ /___ /   /$NC"
Write-Host "$CYAN/_/  |_/_/   /_____//_/|_|$NC"
Write-Host ""
Write-Host "${CYAN}Installing APEX — the universal AI coding agent${NC}"
Write-Host ""

$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "${RED}✗ Python 3.11+ required. Download from https://python.org${NC}"
    exit 1
}

$versionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$versionCheck = python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "${GREEN}✓ Python $versionOutput${NC}"
} else {
    Write-Host "${RED}✗ Python 3.11+ required (found $versionOutput)${NC}"
    exit 1
}

Write-Host ""
Write-Host "${CYAN}Choose installation method:${NC}"
Write-Host "  1) pipx (recommended - isolated)"
Write-Host "  2) pip (user install)"
Write-Host ""
$choice = Read-Host "Enter choice [1]"

if ([string]::IsNullOrEmpty($choice)) { $choice = "1" }

switch ($choice) {
    "1" {
        $hasPipx = Get-Command pipx -ErrorAction SilentlyContinue
        if (-not $hasPipx) {
            Write-Host "${YELLOW}pipx not found. Installing...${NC}"
            pip install pipx
        }
        Write-Host "${CYAN}→ Installing with pipx...${NC}"
        pipx install apex-agent
    }
    "2" {
        Write-Host "${CYAN}→ Installing with pip (user)...${NC}"
        pip install --user apex-agent
    }
    default {
        Write-Host "${RED}Invalid choice${NC}"
        exit 1
    }
}

Write-Host ""
Write-Host "${GREEN}✓ APEX installed!${NC}"
Write-Host ""
Write-Host "  ${CYAN}Get started:${NC}  apex"
Write-Host "  ${CYAN}Set API key:${NC}  `$env:ANTHROPIC_API_KEY='sk-ant-...'"
Write-Host "  ${CYAN}Docs:${NC}         https://apex-agent.dev/docs"
Write-Host ""
Write-Host "${YELLOW}Quick start:${NC}"
Write-Host "  apex                    # Interactive mode"
Write-Host "  apex 'fix my code'      # One-shot mode"
Write-Host "  apex --list-models      # See all models"
Write-Host ""