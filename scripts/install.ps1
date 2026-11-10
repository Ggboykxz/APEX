# ============================================
# APEX installer for Windows (PowerShell)
# https://github.com/Ggboykxz/APEX
#
# APEX ships through two channels: the npm wrapper (`apex`) and the native
# Rust backend (`apex-rs`, headless). PyPI/pip/pipx/uv no longer exist.
#
# Usage:
#   irm https://apex-ai.dev/install.ps1 | iex
#   # or explicitly, with options:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 [options]
#
# Options:
#   -Method auto|npm|native|docker   (default: auto)
#   -Version VER      pin a release (default: latest)
#   -Prefix DIR       install dir for native/docker (default: ~\.apex\bin)
#   -NoPath           do not add the install dir to the user PATH
#   -Yes              do not ask for confirmation
#   -DryRun           print actions without changing anything
#   -Uninstall        uninstall APEX
#   -Purge            with -Uninstall: also remove credentials and config
#   -Help             show this help
# ============================================

[CmdletBinding()]
param(
    [string]$Method = $(if ($env:APEX_METHOD) { $env:APEX_METHOD } else { "auto" }),
    [string]$Version = $(if ($env:APEX_VERSION) { $env:APEX_VERSION } else { "latest" }),
    [string]$Prefix = $(if ($env:APEX_INSTALL_DIR) { $env:APEX_INSTALL_DIR } else { Join-Path $HOME ".apex\bin" }),
    [switch]$NoPath,
    [switch]$Yes,
    [switch]$DryRun,
    [switch]$Uninstall,
    [switch]$Purge,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ESC = [char]27
$CYAN = "$ESC[36m"
$GREEN = "$ESC[32m"
$YELLOW = "$ESC[33m"
$RED = "$ESC[31m"
$MUTED = "$ESC[2m"
$NC = "$ESC[0m"

$Repo = "Ggboykxz/APEX"
$Package = "apex-ai"
$Image = $(if ($env:APEX_IMAGE) { $env:APEX_IMAGE } else { "ghcr.io/ggboykxz/apex" })

function Write-Info([string]$Text) { Write-Host "$CYAN$Text$NC" }
function Write-Ok([string]$Text) { Write-Host "$GREEN$Text$NC" }
function Write-Warn([string]$Text) { Write-Host "$YELLOW$Text$NC" }
function Write-Muted([string]$Text) { Write-Host "$MUTED$Text$NC" }
function Fail([string]$Text) { Write-Host "$RED$Text$NC"; exit 1 }

function Show-Usage {
    if ($PSCommandPath -and (Test-Path -LiteralPath $PSCommandPath)) {
        $lines = Get-Content -LiteralPath $PSCommandPath | Select-Object -First 24
        foreach ($line in $lines) { Write-Host ($line -replace '^# ?', '') }
        return
    }
    Write-Host "Usage: install.ps1 [-Method auto|npm|native|docker] [-Version VER] [-Prefix DIR] [-NoPath] [-Yes] [-DryRun] [-Uninstall [-Purge]]"
}

if ($Help) { Show-Usage; exit 0 }

if ($Version.StartsWith("v")) { $Version = $Version.Substring(1) }
if ([string]::IsNullOrWhiteSpace($Version)) { $Version = "latest" }
if ($Prefix.StartsWith("~")) { $Prefix = $Prefix -replace '^~', $HOME }

if ($Method -notin @("auto", "npm", "native", "docker")) {
    Fail "Unknown method '$Method' (auto|npm|native|docker)"
}

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-Step {
    param([scriptblock]$Action, [string]$Preview)
    if ($DryRun) { Write-Muted "  would run: $Preview"; return }
    & $Action
}

function Confirm-Action([string]$Question) {
    if ($Yes -or $DryRun) { return $true }
    $answer = Read-Host "$Question [y/N]"
    return ($answer -match '^(y|yes)$')
}

function Download-File([string]$Url, [string]$OutFile) {
    if ($DryRun) { Write-Muted "  would download: $Url"; return }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

function Add-UserPath([string]$Directory) {
    if ($NoPath) { Write-Warn "Skipping PATH update (-NoPath)."; return }

    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $current) { $current = "" }
    $entries = $current.Split(';', [System.StringSplitOptions]::RemoveEmptyEntries)
    if ($entries -contains $Directory) {
        Write-Ok "PATH already contains $Directory"
        return
    }
    if ($DryRun) {
        Write-Muted "  would add $Directory to the user PATH"
        return
    }
    $updated = (@($entries) + $Directory) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $updated, "User")
    $env:Path = "$Directory;$env:Path"
    Write-Ok "Added $Directory to the user PATH (open a new terminal)"
}

function Remove-UserPath([string]$Directory) {
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $current) { return }
    $entries = $current.Split(';', [System.StringSplitOptions]::RemoveEmptyEntries)
    if ($entries -notcontains $Directory) { return }
    if ($DryRun) {
        Write-Muted "  would remove $Directory from the user PATH"
        return
    }
    $updated = ($entries | Where-Object { $_ -ne $Directory }) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $updated, "User")
    Write-Ok "Removed $Directory from the user PATH"
}

function Remove-Target([string]$Target) {
    if (Test-Path -LiteralPath $Target) {
        if ($DryRun) {
            Write-Muted "  would remove: $Target"
            return
        }
        Remove-Item -LiteralPath $Target -Recurse -Force
        Write-Ok "Removed $Target"
    }
}

function Get-Architecture {
    $raw = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
    switch ($raw.ToString()) {
        "X64" { return "x86_64" }
        "Arm64" { return "aarch64" }
        default { Fail "Unsupported architecture: $raw" }
    }
}

# -- Uninstall --------------------------------------------------------------

function Uninstall-Apex {
    Write-Info "Uninstalling APEX..."
    if (-not (Confirm-Action "Remove APEX from this machine?")) {
        Write-Warn "Cancelled."
        exit 0
    }

    Remove-Target (Join-Path $Prefix "apex-rs.exe")
    Remove-Target (Join-Path $Prefix "apex.cmd")
    if ((Test-Path -LiteralPath $Prefix) -and -not (Get-ChildItem -LiteralPath $Prefix -Force)) {
        Invoke-Step -Preview "Remove-Item '$Prefix'" -Action { Remove-Item -LiteralPath $Prefix -Force }
    }

    if (Test-Command "npm") { Invoke-Step -Preview "npm uninstall -g $Package" -Action { & npm uninstall -g $Package } }

    Remove-Target (Join-Path $HOME ".config\apex")
    Remove-Target (Join-Path $HOME ".apex\sessions")
    Remove-Target (Join-Path $HOME ".apex\memory")
    Remove-Target (Join-Path $HOME ".apex\tasks")
    Remove-UserPath $Prefix

    if ($Purge) {
        Remove-Target (Join-Path $HOME ".apex")
    } else {
        Write-Muted "Kept: $HOME\.apex\api_keys.json, $HOME\.apex\gateway.json (use -Purge to remove)"
    }
    Write-Ok "APEX uninstalled."
}

# -- Install methods --------------------------------------------------------

function Install-Npm {
    if (-not (Test-Command "npm")) { Fail "npm is not installed (https://nodejs.org)" }
    $spec = $Package
    if ($Version -ne "latest") { $spec = "$Package@$Version" }

    Write-Info "Installing $spec globally with npm..."
    Write-Muted "The npm wrapper downloads the verified apex-rs backend on first run."
    if (-not (Confirm-Action "Install APEX via npm?")) {
        Write-Warn "Cancelled."
        exit 0
    }
    Invoke-Step -Preview "npm install -g $spec" -Action { & npm install -g $spec }
    Write-Ok "APEX installed."
    Write-Muted "Run: apex"
}

function Install-Native {
    $arch = Get-Architecture
    $asset = "apex-rs-$arch-pc-windows-msvc.zip"
    if ($Version -eq "latest") {
        $base = "https://github.com/$Repo/releases/latest/download"
    } else {
        $base = "https://github.com/$Repo/releases/download/v$Version"
    }

    Write-Info "Installing the native backend ($asset)..."
    Write-Muted "The native backend is headless (serve, run, tools). Install via npm for an 'apex' command."
    if (-not (Confirm-Action "Download the native backend from GitHub?")) {
        Write-Warn "Cancelled."
        exit 0
    }

    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("apex-native-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    try {
        $archive = Join-Path $tmp $asset
        $sidecar = "$archive.sha256"
        Download-File "$base/$asset" $archive
        Download-File "$base/$asset.sha256" $sidecar

        if (-not $DryRun) {
            $expected = ((Get-Content -LiteralPath $sidecar -Raw) -split '\s+')[0].ToLower()
            $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower()
            if (-not $expected -or $expected -ne $actual) {
                Fail "Checksum mismatch for $asset - refusing to install."
            }
            Write-Ok "Checksum verified."

            $unpacked = Join-Path $tmp "unpack"
            Expand-Archive -LiteralPath $archive -DestinationPath $unpacked -Force
            $binary = Get-ChildItem -LiteralPath $unpacked -Recurse -Filter "apex-rs.exe" | Select-Object -First 1
            if (-not $binary) { Fail "The archive does not contain apex-rs.exe" }
            New-Item -ItemType Directory -Path $Prefix -Force | Out-Null
            Copy-Item -LiteralPath $binary.FullName -Destination (Join-Path $Prefix "apex-rs.exe") -Force
        } else {
            Write-Muted "  would verify the checksum and install apex-rs.exe to $Prefix"
        }
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }

    if ($DryRun) {
        Write-Muted "  would install apex-rs.exe to $Prefix"
    } else {
        Write-Ok "Native backend installed at $Prefix\apex-rs.exe"
    }
    Add-UserPath $Prefix
}

function Install-Docker {
    if (-not (Test-Command "docker")) { Fail "docker is not installed" }
    Write-Info ("Creating the Docker launcher (image {0}:{1})..." -f $Image, $Version)
    if (-not (Confirm-Action "Install a Docker-based 'apex' launcher?")) {
        Write-Warn "Cancelled."
        exit 0
    }
    Invoke-Step -Preview "New-Item -ItemType Directory '$Prefix'" -Action { New-Item -ItemType Directory -Path $Prefix -Force | Out-Null }
    $launcher = Join-Path $Prefix "apex.cmd"
    if ($DryRun) {
        Write-Muted "  would write $launcher"
    } else {
        $lines = @(
            "@echo off",
            ("docker run -it --rm -v `"%CD%:/workspace`" -w /workspace " +
                "-e OPENAI_API_KEY -e ANTHROPIC_API_KEY -e GOOGLE_API_KEY " +
                "-e GROQ_API_KEY -e DEEPSEEK_API_KEY -e OPENROUTER_API_KEY " +
                ("{0}:{1} %*" -f $Image, $Version))
        )
        Set-Content -LiteralPath $launcher -Value $lines -Encoding ASCII
    }
    Write-Ok "Docker launcher installed at $launcher"
    Add-UserPath $Prefix
}

# -- Main -------------------------------------------------------------------

Write-Host ""
Write-Host "$CYAN  APEX$NC"
Write-Host "$MUTED  The universal AI coding agent. Every model. One terminal.$NC"
Write-Host ""

if ($Uninstall) {
    Uninstall-Apex
    exit 0
}
if ($Purge) { Fail "-Purge is only valid with -Uninstall" }

switch ($Method) {
    "npm" { Install-Npm }
    "native" { Install-Native }
    "docker" { Install-Docker }
    default { Install-Native }
}

Write-Host ""
Write-Ok "Done."
Write-Muted "apex-rs --version  (npm: apex --version)"
