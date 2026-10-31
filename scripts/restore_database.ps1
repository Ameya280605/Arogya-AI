<#
.SYNOPSIS
    Arogya AI - PostgreSQL Database Restore & Recovery Automation Script
.DESCRIPTION
    Wraps scripts/restore_database.py to safely restore a custom-format
    PostgreSQL backup into an explicitly designated disposable restore-test database.
    Prevents accidental overwrites of the application database and verifies restored schema.
.PARAMETER BackupFile
    Path to existing .dump archive file.
.PARAMETER TargetDb
    Name of the separate, disposable restore-test database (e.g. arogya_restore_test).
.PARAMETER ConfirmRestoreTarget
    Mandatory confirmation string matching TargetDb exactly.
.PARAMETER PgRestorePath
    Explicit path to pg_restore binary.
.PARAMETER CleanupTarget
    If specified, drops the disposable test database after successful verification.
.PARAMETER ConfirmCleanup
    Mandatory confirmation matching TargetDb if -CleanupTarget is passed.
.PARAMETER Json
    If specified, emits output formatted as JSON.
.PARAMETER Quiet
    Suppresses human-readable informational banners.
.EXAMPLE
    .\scripts\restore_database.ps1 -BackupFile "backups\arogya_ai_backup_20261025.dump" -TargetDb "arogya_restore_test" -ConfirmRestoreTarget "arogya_restore_test"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,

    [Parameter(Mandatory=$true)]
    [string]$TargetDb,

    [Parameter(Mandatory=$true)]
    [string]$ConfirmRestoreTarget,

    [string]$PgRestorePath,
    [switch]$CleanupTarget,
    [string]$ConfirmCleanup,
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
$RestoreScript = Join-Path $RepoRoot "scripts\restore_database.py"
$ScriptArgs = @(
    $RestoreScript,
    "--backup-file", $BackupFile,
    "--target-db", $TargetDb,
    "--confirm-restore-target", $ConfirmRestoreTarget
)

if ($PgRestorePath) {
    $ScriptArgs += @("--pg-restore-path", $PgRestorePath)
}
if ($CleanupTarget) {
    $ScriptArgs += "--cleanup-target"
}
if ($ConfirmCleanup) {
    $ScriptArgs += @("--confirm-cleanup", $ConfirmCleanup)
}
if ($Json) {
    $ScriptArgs += "--json"
}
if ($Quiet) {
    $ScriptArgs += "--quiet"
}

# 4. Execute restore utility
& $PythonExe @ScriptArgs
exit $LASTEXITCODE
