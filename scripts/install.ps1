# ============================================
# APEX Installer for Windows (PowerShell)
# https://github.com/Ggboykxz/APEX
# ============================================

$ErrorActionPreference = "Stop"

$CYAN = "`e[36m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$RED = "`e[31m"
$MUTED = "`e[2m"
$NC = "`e[0m"

Write-Host ""
Write-Host "$CYAN  APEX$NC"
Write-Host "$MUTED  The universal AI coding agent. Every model. One terminal.$NC"
Write-Host ""

$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "$RED Python 3.11+ required. Download from https://python.org$NC"
    exit 1
}

$versionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$versionCheck = python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "$GREEN Python $versionOutput$NC"
} else {
    Write-Host "$RED Python 3.11+ required (found $versionOutput)$NC"
    exit 1
}

Write-Host ""
Write-Host "$CYAN Choose installation method:$NC"
Write-Host "  1) uv (recommended - fastest)"
Write-Host "  2) pipx (isolated)"
Write-Host "  3) pip (user install)"
Write-Host "  4) Docker (containerized)"
Write-Host ""
$choice = Read-Host "Enter choice [1]"

if ([string]::IsNullOrEmpty($choice)) { $choice = "1" }

switch ($choice) {
    "1" {
        $hasUv = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $hasUv) {
            Write-Host "$YELLOW uv not found. Installing...$NC"
            irm https://astral.sh/uv/install.ps1 | iex
        }
        Write-Host "$CYAN Installing with uv...$NC"
        uv tool install apex-ai
    }
    "2" {
        $hasPipx = Get-Command pipx -ErrorAction SilentlyContinue
        if (-not $hasPipx) {
            Write-Host "$YELLOW pipx not found. Installing...$NC"
            pip install pipx
        }
        Write-Host "$CYAN Installing with pipx...$NC"
        pipx install apex-ai
    }
    "3" {
        Write-Host "$CYAN Installing with pip (user)...$NC"
        pip install --user apex-ai
    }
    "4" {
        Write-Host "$CYAN Pulling Docker image...$NC"
        docker pull ghcr.io/ggboykxz/apex:latest
        Write-Host ""
        Write-Host "$GREEN Run with:$NC"
        Write-Host "  docker run -it -v `${PWD}:/workspace ghcr.io/ggboykxz/apex"
        exit 0
    }
    default {
        Write-Host "$RED Invalid choice$NC"
        exit 1
    }
}

Write-Host ""
Write-Host "$GREEN APEX installed successfully!$NC"
Write-Host ""
Write-Host "  $CYAN Get started:$NC  apex"
Write-Host "  $CYAN Set API key:$NC  `$env:ANTHROPIC_API_KEY='sk-ant-...'"
Write-Host "  $CYAN TUI mode:$NC     apex --tui"
Write-Host "  $CYAN Docs:$NC         https://apex-ai.dev/docs"
Write-Host ""
