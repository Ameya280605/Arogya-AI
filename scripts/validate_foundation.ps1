<#
.SYNOPSIS
    Arogya AI - Foundation Structure & Repository Hygiene Validator
.DESCRIPTION
    Validates repository root, required directory taxonomy, core hygiene files,
    governance documents, and Git isolation boundaries for Module 1.
    This script is dependency-free, read-only, and non-destructive.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# 1. Resolve repository root relative to script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Arogya AI - Foundation Validation" -ForegroundColor Cyan
Write-Host "Target Root: $RepoRoot" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Failures = [System.Collections.Generic.List[string]]::new()

# 2. Verify Git root matches RepoRoot
try {
    $rawGitRoot = git -C $RepoRoot rev-parse --show-toplevel 2>$null
    if (-not $rawGitRoot) {
        $Failures.Add("Git is not initialized in this workspace.")
    } else {
        $gitRoot = [System.IO.Path]::GetFullPath($rawGitRoot).TrimEnd([char]'/', [char]'\')
        $expectedRoot = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd([char]'/', [char]'\')
        if ($gitRoot -ne $expectedRoot) {
            $Failures.Add("Git root mismatch: resolved '$gitRoot', expected '$expectedRoot'")
        }
    }
} catch {
    $Failures.Add("Failed to execute Git command to verify repository root.")
}

# 3. Verify top-level directories
$RequiredDirs = @(
    "backend",
    "frontend",
    "ml",
    "data",
    "knowledge",
    "docs",
    "tests",
    "scripts",
    "deployment"
)

foreach ($dir in $RequiredDirs) {
    $path = Join-Path $RepoRoot $dir
    if (-not (Test-Path -Path $path -PathType Container)) {
        $Failures.Add("Missing required top-level directory: $dir")
    }
}

# 4. Verify required root foundation files
$RequiredRootFiles = @(
    "README.md",
    ".gitignore",
    ".env.example",
    ".editorconfig",
    ".gitattributes",
    "CONTRIBUTING.md",
    "LICENSE_DECISION.md"
)

foreach ($file in $RequiredRootFiles) {
    $path = Join-Path $RepoRoot $file
    if (-not (Test-Path -Path $path -PathType Leaf)) {
        $Failures.Add("Missing required foundation file: $file")
    }
}

# 5. Verify required architecture & governance documentation
$RequiredDocs = @(
    "docs/architecture/ARCHITECTURE.md",
    "docs/architecture/MODULE_DEPENDENCIES.md",
    "docs/architecture/DECISION_LOG.md",
    "docs/governance/INTENDED_USE_AND_NON_GOALS.md",
    "docs/governance/DATA_GOVERNANCE.md"
)

foreach ($doc in $RequiredDocs) {
    $path = Join-Path $RepoRoot $doc
    if (-not (Test-Path -Path $path -PathType Leaf)) {
        $Failures.Add("Missing required documentation file: $doc")
    }
}

# 6. Verify .env.example is not ignored by Git
$envExamplePath = Join-Path $RepoRoot ".env.example"
if (Test-Path $envExamplePath) {
    & git -C $RepoRoot check-ignore -q .env.example
    # git check-ignore returns 0 if ignored, 1 if not ignored
    if ($LASTEXITCODE -eq 0) {
        $Failures.Add(".env.example is erroneously ignored by Git.")
    }
}

# 7. Confirm no actual .env is tracked in Git
$trackedEnv = & git -C $RepoRoot ls-files .env 2>$null
if ($trackedEnv) {
    $Failures.Add("Security Alert: An actual .env file is tracked in Git.")
}

# 8. Report results
if ($Failures.Count -gt 0) {
    Write-Host ""
    Write-Host "Foundation Validation FAILED with $($Failures.Count) issue(s):" -ForegroundColor Red
    foreach ($f in $Failures) {
        Write-Host "  [X] $f" -ForegroundColor Red
    }
    exit 1
}

Write-Host ""
Write-Host "[OK] Foundation validation PASSED: all required directories, files, and git boundaries verified." -ForegroundColor Green
exit 0
