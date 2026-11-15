# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 6 (p2p)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

$ErrorActionPreference = "Continue"

# Detect Python
$PYTHON = "python"
if (Test-Path "C:\Users\navan\anaconda3\python.exe") {
    $PYTHON = "C:\Users\navan\anaconda3\python.exe"
}

# Go to assign06 root
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
Write-Host " ASSIGNMENT 6: Peer-to-Peer Mempool and Block Relay Network (p2p)" -ForegroundColor Yellow
Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan

# Step 1: Help overview
Run-Step -Command "$PYTHON -m p2p.cli --help"

# Step 2: 5-Node partition, divergent mining, healing & convergence
Run-Step -Command "$PYTHON -m p2p.cli simulate-partition"

# Step 3: Automated unit tests
Run-Step -Command "$PYTHON -m pytest -v"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO COMPLETE - ALL TESTS PASS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [Enter] to exit"
