# ============================================
# APEX installer entry point for Windows (PowerShell)
# https://github.com/Ggboykxz/APEX
#
# This file only dispatches to the canonical installer, `scripts/install.ps1`,
# so the one-liner documented on the website keeps working:
#
#   irm https://raw.githubusercontent.com/Ggboykxz/APEX/main/install.ps1 | iex
#
# APEX ships through npm and the native Rust backend only; PyPI/pip/pipx/uv
# channels were removed.
# ============================================

$ErrorActionPreference = "Stop"

$here = $null
if ($PSCommandPath -and (Test-Path -LiteralPath $PSCommandPath)) {
    $here = Split-Path -Parent $PSCommandPath
}

if ($here -and (Test-Path -LiteralPath (Join-Path $here "scripts\install.ps1"))) {
    & (Join-Path $here "scripts\install.ps1") @args
    exit $LASTEXITCODE
}

$ref = if ($env:APEX_REF) { $env:APEX_REF } else { "main" }
$url = "https://raw.githubusercontent.com/Ggboykxz/APEX/$ref/scripts/install.ps1"
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("apex-install-" + [guid]::NewGuid().ToString("N") + ".ps1")

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
    & $tmp @args
    exit $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
