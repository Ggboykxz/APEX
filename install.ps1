# ============================================
# APEX v1.2.0 Installer for Windows (PowerShell)
# https://github.com/Ggboykxz/APEX
# ============================================

$ErrorActionPreference = "Stop"

$CYAN = "`e[0;36m"
$GREEN = "`e[0;32m"
$YELLOW = "`e[0;33m"
$RED = "`e[0;31m"
$MUTED = "`e[0;90m"
$BOLD = "`e[1m"
$NC = "`e[0m"

$APEX_VERSION = "1.2.0"
$version = ""
$uninstall = $false
$defaultModel = ""

# Parse arguments
for ($i = 0; $i -lt $args.Length; $i++) {
    switch ($args[$i]) {
        "-h" { Show-Help; exit 0 }
        "--help" { Show-Help; exit 0 }
        "-v" { $version = $args[++$i] }
        "--version" { $version = $args[++$i] }
        "-u" { $uninstall = $true }
        "--uninstall" { $uninstall = $true }
        "-m" { $defaultModel = $args[++$i] }
        "--model" { $defaultModel = $args[++$i] }
    }
}

function Show-Help {
    Write-Host ""
    Write-Host "$CYAN$BOLD  APEX Installer for Windows$NC"
    Write-Host ""
    Write-Host "  The universal AI coding agent. Every model. One terminal."
    Write-Host ""
    Write-Host "$GREEN  Usage:$NC"
    Write-Host "    irm https://raw.githubusercontent.com/Ggboykxz/APEX/main/install.ps1 | iex"
    Write-Host "    .\install.ps1 [options]"
    Write-Host ""
    Write-Host "$GREEN  Options:$NC"
    Write-Host "    -h, --help              Display this help"
    Write-Host "    -v, --version <ver>     Install a specific version"
    Write-Host "    -u, --uninstall         Remove APEX"
    Write-Host "    -m, --model <model>     Set default model"
    Write-Host ""
    Write-Host "$GREEN  Requirements:$NC"
    Write-Host "    - Python 3.11+"
    Write-Host "    - pip or pipx"
    Write-Host ""
}

function Uninstall-Apex {
    Write-Host "$MUTED Removing APEX...$NC"
    $apexCmd = Get-Command apex -ErrorAction SilentlyContinue
    if ($apexCmd) {
        pip uninstall -y apex-ai 2>$null
        pipx uninstall apex-ai 2>$null
        uv tool uninstall apex-ai 2>$null
    }
    Remove-Item -Force "$env:USERPROFILE\.local\bin\apex.exe" -ErrorAction SilentlyContinue
    Write-Host "$GREEN APEX removed successfully!$NC"
}

function Install-With-Uv {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) { return $false }

    Write-Host "$MUTED Installing with uv (fastest)...$NC"
    if ($version) {
        uv tool install "apex-ai==$version"
    } else {
        uv tool install apex-ai
    }
    return $true
}

function Install-With-Pipx {
    $pipx = Get-Command pipx -ErrorAction SilentlyContinue
    if (-not $pipx) { return $false }

    Write-Host "$MUTED Installing with pipx...$NC"
    if ($version) {
        pipx install "apex-ai==$version"
    } else {
        pipx install apex-ai
    }
    return $true
}

function Install-With-Pip {
    $pip = Get-Command pip -ErrorAction SilentlyContinue
    if (-not $pip) {
        $pip = Get-Command pip3 -ErrorAction SilentlyContinue
    }
    if (-not $pip) { return $false }

    Write-Host "$MUTED Installing with pip...$NC"
    if ($version) {
        pip install "apex-ai==$version" --user
    } else {
        pip install apex-ai --user
    }
    return $true
}

function Install-With-Docker {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) { return $false }

    Write-Host "$MUTED Pulling APEX Docker image...$NC"
    docker pull ghcr.io/ggboykxz/apex:latest
    Write-Host ""
    Write-Host "$GREEN Docker image pulled! Run with:$NC"
    Write-Host "  docker run -it -v `${PWD}:/workspace ghcr.io/ggboykxz/apex"
    return $true
}

# Main
if ($uninstall) {
    Uninstall-Apex
    exit 0
}

Write-Host ""
Write-Host "$CYAN$BOLD  APEX v$APEX_VERSION$NC"
Write-Host "$MUTED  The universal AI coding agent. Every model. One terminal.$NC"
Write-Host ""

# Check Python
$pythonExe = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonExe) {
    $pythonExe = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonExe) {
    Write-Host "$RED Python 3.11+ required. Download from https://python.org$NC"
    Write-Host "$MUTED Or use Docker: docker run -it ghcr.io/ggboykxz/apex$NC"
    exit 1
}

$pyVersion = & $pythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$versionOk = & $pythonExe -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "$RED Python 3.11+ required (found $pyVersion)$NC"
    exit 1
}
Write-Host "$GREEN Python $pyVersion detected$NC"
Write-Host ""

# Install
$success = $false

$success = Install-With-Uv
if (-not $success) { $success = Install-With-Pipx }
if (-not $success) { $success = Install-With-Pip }

if (-not $success) {
    Write-Host ""
    Write-Host "$RED Installation failed!$NC"
    Write-Host "$MUTED Try one of:$NC"
    Write-Host "  pip install apex-ai"
    Write-Host "  pipx install apex-ai"
    Write-Host "  uv tool install apex-ai"
    Write-Host "  docker run -it ghcr.io/ggboykxz/apex"
    exit 1
}

# Set default model
if ($defaultModel) {
    $apexDir = "$env:USERPROFILE\.apex"
    if (-not (Test-Path $apexDir)) { New-Item -ItemType Directory -Path $apexDir }
    @{ model = $defaultModel } | ConvertTo-Json | Set-Content "$apexDir\config.json"
    Write-Host "$MUTED Default model set to: $defaultModel$NC"
}

Write-Host ""
Write-Host "$GREEN$BOLD APEX v$APEX_VERSION installed successfully!$NC"
Write-Host ""
Write-Host "  $CYAN 1.$NC Set your API key:"
Write-Host "     `$env:ANTHROPIC_API_KEY='sk-ant-...'"
Write-Host ""
Write-Host "  $CYAN 2.$NC Launch APEX:"
Write-Host "     $GREEN apex$NC"
Write-Host ""
Write-Host "  $MUTED Free models (no API key needed):$NC"
Write-Host "     $GREEN apex --model ollama-llama3$NC"
Write-Host ""
Write-Host "  $MUTED TUI mode:$NC"
Write-Host "     $GREEN apex --tui$NC"
Write-Host ""
