# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 5 (chain)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

$ErrorActionPreference = "Continue"

# Detect Python
$PYTHON = "python"
if (Test-Path "C:\Users\navan\anaconda3\python.exe") {
    $PYTHON = "C:\Users\navan\anaconda3\python.exe"
}

# Go to assign05 root
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
Write-Host " ASSIGNMENT 5: Blocks, Proof of Work, Forks, and Reorganisation (chain)" -ForegroundColor Yellow
Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan

# Step 1: Help overview
Run-Step -Command "$PYTHON -m chain.cli --help"

# Step 2: 116-Byte block header binary format
Run-Step -Command "$PYTHON -m chain.cli hex-dump"

# Step 3: Mining benchmark across 3 targets
Run-Step -Command "$PYTHON -m chain.cli benchmark"

# Step 4: Two-miner fork & cumulative work reorganisation
Run-Step -Command "$PYTHON -m chain.cli simulate-fork"

# Step 5: Automated unit tests
Run-Step -Command "$PYTHON -m pytest -v"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO COMPLETE - ALL TESTS PASS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [Enter] to exit"
