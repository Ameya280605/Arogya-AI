<#
.SYNOPSIS
    Arogya AI - Local Backend Execution & Test Automation Script
.DESCRIPTION
    Launches the FastAPI development server or executes the pytest test suite
    using the isolated project virtual environment (.venv).
.PARAMETER Test
    If specified, executes pytest instead of starting the web server.
.PARAMETER BindHost
    Network interface to bind (default: 127.0.0.1 / localhost loopback only).
.PARAMETER Port
    TCP port for the API server (default: 8000).
.PARAMETER NoReload
    Disables the ASGI server file-watcher auto-reload.
.EXAMPLE
    .\scripts\run_backend.ps1
.EXAMPLE
    .\scripts\run_backend.ps1 -Test
.EXAMPLE
    .\scripts\run_backend.ps1 -Port 8080
#>

[CmdletBinding()]
param(
    [switch]$Test,
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

# 1. Resolve repository root relative to script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

# 2. Verify virtual environment exists
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at: $RepoRoot\.venv" -ForegroundColor Red
    Write-Host "Please create and configure the environment before running:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt" -ForegroundColor Yellow
    exit 1
}

# 3. Test execution mode
if ($Test) {
    Write-Host "Running Arogya AI backend test suite..." -ForegroundColor Cyan
    Set-Location $RepoRoot
    & $PythonExe -m pytest
    exit $LASTEXITCODE
}

# 4. Local Development Server mode
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Arogya AI - Local Backend Development Server" -ForegroundColor Cyan
Write-Host "Binding: http://$BindHost`:$Port" -ForegroundColor Cyan
Write-Host "Application: backend.app.main:app" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Loopback safety notice
if ($BindHost -ne "127.0.0.1" -and $BindHost -ne "localhost") {
    Write-Host "[WARNING] Binding to non-loopback interface ($BindHost). Ensure this is intentional for development." -ForegroundColor Yellow
}

$UvicornArgs = @(
    "-m", "uvicorn",
    "backend.app.main:app",
    "--host", $BindHost,
    "--port", [string]$Port
)

if (-not $NoReload) {
    $UvicornArgs += "--reload"
}

Set-Location $RepoRoot
& $PythonExe $UvicornArgs
exit $LASTEXITCODE
