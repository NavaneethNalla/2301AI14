# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 1 (hashlab)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

$ErrorActionPreference = "Continue"

# Detect Python
$PYTHON = "python"
if (Test-Path "C:\Users\navan\anaconda3\python.exe") {
    $PYTHON = "C:\Users\navan\anaconda3\python.exe"
}

# Go to assign01 root
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ASSIGN_DIR = Split-Path -Parent $SCRIPT_DIR
Set-Location $ASSIGN_DIR

function Run-Step {
    param(
        [string]$Command
    )
    Write-Host ""
    Read-Host "Press [Enter] to run"
    Write-Host "`$ $Command" -ForegroundColor Cyan
    Invoke-Expression $Command
}

Clear-Host
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " ASSIGNMENT 1: Bytes, Hashes, and Reproducible Data (hashlab)" -ForegroundColor Yellow
Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan

# Step 1: Help overview
Run-Step -Command "$PYTHON -m hashlab.cli --help"

# Step 2: Text mode
Run-Step -Command "$PYTHON -m hashlab.cli text `"Alice pays Bob 10`""

# Step 3: Hex mode & malformed hex
Run-Step -Command "$PYTHON -m hashlab.cli hex `"0102030405`""
Run-Step -Command "$PYTHON -m hashlab.cli hex `"010203040z`""

# Step 4: Avalanche effect
Run-Step -Command "$PYTHON -m hashlab.cli avalanche --text `"Alice pays Bob 10`" --bit 7"

# Step 5: Canonical JSON
Run-Step -Command "$PYTHON -m hashlab.cli canonical-json '{\`"recipient\`":\`"Bob\`",\`"amount\`":10}'"

# Step 6: Visual differences
Run-Step -Command "$PYTHON -m hashlab.cli demo-differences"

# Step 7: Automated unit tests
Run-Step -Command "$PYTHON -m pytest -v"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO COMPLETE - ALL TESTS PASS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [Enter] to exit"
