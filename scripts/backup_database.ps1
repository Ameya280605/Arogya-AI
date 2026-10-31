<#
.SYNOPSIS
    Arogya AI - PostgreSQL Database Backup Automation Script
.DESCRIPTION
    Wraps scripts/backup_database.py to create consistent, timestamped,
    non-overwriting PostgreSQL custom-format backups (.dump) using the isolated
    virtual environment. Passwords and credentials are never passed via command-line arguments.
.PARAMETER Destination
    Target directory for backup file (default: <repo_root>\backups).
.PARAMETER PgDumpPath
    Explicit path to pg_dump executable.
.PARAMETER Json
    If specified, emits output formatted as JSON.
.PARAMETER Quiet
    Suppresses human-readable informational banners.
.EXAMPLE
    .\scripts\backup_database.ps1
.EXAMPLE
    .\scripts\backup_database.ps1 -Destination "D:\ArogyaBackups"
.EXAMPLE
    .\scripts\backup_database.ps1 -Json
#>

[CmdletBinding()]
param(
    [string]$Destination,
    [string]$PgDumpPath,
    [switch]$Json,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

# 1. Resolve repository root relative to script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

# 2. Verify virtual environment exists
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at: $RepoRoot\.venv" -ForegroundColor Red
    Write-Host "Please create and configure the environment before running." -ForegroundColor Yellow
    exit 1
}

# 3. Assemble arguments
$BackupScript = Join-Path $RepoRoot "scripts\backup_database.py"
$ScriptArgs = @($BackupScript)

if ($Destination) {
    $ScriptArgs += @("--destination", $Destination)
}
if ($PgDumpPath) {
    $ScriptArgs += @("--pg-dump-path", $PgDumpPath)
}
if ($Json) {
    $ScriptArgs += "--json"
}
if ($Quiet) {
    $ScriptArgs += "--quiet"
}

# 4. Execute backup utility
& $PythonExe @ScriptArgs
exit $LASTEXITCODE
