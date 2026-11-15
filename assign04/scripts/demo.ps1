# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 4 (utxo)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

$ErrorActionPreference = "Continue"

# Detect Python
$PYTHON = "python"
if (Test-Path "C:\Users\navan\anaconda3\python.exe") {
    $PYTHON = "C:\Users\navan\anaconda3\python.exe"
}

# Go to assign04 root
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ASSIGN_DIR = Split-Path -Parent $SCRIPT_DIR
Set-Location $ASSIGN_DIR

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " VIDEO RECORDING RUNNER: ASSIGNMENT 4 (utxo)" -ForegroundColor Yellow
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
    -Speech "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 4: A UTXO Ledger and Transaction Validator using the 'utxo' tool." `
    -Command "$PYTHON -m utxo.cli --help"

# STEP 2
Prompt-Step -StepNum 2 `
    -Title "Running Alice-Pays-Bob Scenario & Double-Spend Attack Rejection" `
    -Speech "Here we execute the canonical Alice-pays-Bob scenario: Alice consumes 40 and 70 units, pays 85 to Bob with fee 2, and receives 23 change. When the exact same transaction is submitted a second time, the ledger rejects it as a double-spend attempt." `
    -Command "$PYTHON -m utxo.cli demo-alice-bob"

# STEP 3
Prompt-Step -StepNum 3 `
    -Title "Automated Test Suite Verification" `
    -Speech "Finally, we run the automated pytest test suite. All 22 tests pass covering P2PKH validation, coin selection, atomic rollbacks, and double-spend prevention. Thank you!" `
    -Command "$PYTHON -m pytest -v"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO FOR ASSIGNMENT 4 COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [ENTER] to exit runner..."
