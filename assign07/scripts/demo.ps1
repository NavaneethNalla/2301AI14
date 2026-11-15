# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 7 (Escrow)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

$ErrorActionPreference = "Continue"

# Detect npm
$NPM = "npm"
if (Get-Command "npm.cmd" -ErrorAction SilentlyContinue) {
    $NPM = "npm.cmd"
}

# Go to assign07 root
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
Write-Host " ASSIGNMENT 7: Solidity Escrow from Specification to Deployment (Escrow)" -ForegroundColor Yellow
Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan

# Step 1: Deploy and interaction script
Run-Step -Command "& `"$NPM`" run deploy"

# Step 2: Automated Hardhat test suite
Run-Step -Command "& `"$NPM`" test"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO COMPLETE - ALL TESTS PASS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [Enter] to exit"
