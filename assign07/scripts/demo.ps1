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

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " VIDEO RECORDING RUNNER: ASSIGNMENT 7 (Escrow)" -ForegroundColor Yellow
    Write-Host " Course : Practical Blockchain Engineering (Dr. Mayank Agarwal, IIT Patna)" -ForegroundColor White
    Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Prompt-Step {
    param(
        [int]$StepNum,
        [string]$Title,
        [string]$Speech,
        [string]$Command
    )
    Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "[STEP $StepNum] $Title" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "[SAY THIS ALOUD]:" -ForegroundColor Cyan
    Write-Host "$Speech`n" -ForegroundColor White
    Write-Host "[COMMAND]:" -ForegroundColor DarkYellow
    Write-Host "$Command`n" -ForegroundColor DarkGray
    Read-Host ">>> Press [ENTER] to run command and show output..."
    Write-Host ""
    Invoke-Expression $Command
    Write-Host ""
    Write-Host "[COMPLETED STEP $StepNum]" -ForegroundColor Green
    Write-Host ""
}

Show-Header

# STEP 1
Prompt-Step -StepNum 1 `
    -Title "Introduction" `
    -Speech "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14, from IIT Patna. Today I am demonstrating Assignment 7: Solidity Escrow from Specification to Deployment." `
    -Command "Get-Content package.json"

# STEP 2
Prompt-Step -StepNum 2 `
    -Title "Deploying Escrow Contract & End-to-End Interaction" `
    -Speech "Now we execute the automated deployment and interaction script. It deploys the Escrow contract, funds 2.0 ETH as Buyer, releases payment to Seller, executes a pull-payment withdrawal, verifies contract solvency, and logs the gas report." `
    -Command "& `"$NPM`" run deploy"

# STEP 3
Prompt-Step -StepNum 3 `
    -Title "Automated Unit & Fuzz Test Suite Verification" `
    -Speech "Finally, we run the automated Hardhat test suite. All 23 unit and fuzz tests pass covering every state transition, access control rejection, and pull withdrawal. Thank you!" `
    -Command "& `"$NPM`" test"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO FOR ASSIGNMENT 7 COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [ENTER] to exit runner..."
