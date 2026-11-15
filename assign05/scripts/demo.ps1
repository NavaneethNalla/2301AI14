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

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " VIDEO RECORDING RUNNER: ASSIGNMENT 5 (chain)" -ForegroundColor Yellow
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
    -Speech "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 5: Blocks, Proof of Work, Forks, and Reorganisation using the 'chain' tool." `
    -Command "$PYTHON -m chain.cli --help"

# STEP 2
Prompt-Step -StepNum 2 `
    -Title "Canonical 116-Byte Block Header Binary Format" `
    -Speech "Here we inspect the annotated 116-byte binary block header format: version, previous block hash, Merkle root, timestamp, target, and nonce. Double-SHA256 of these bytes forms the block hash." `
    -Command "$PYTHON -m chain.cli hex-dump"

# STEP 3
Prompt-Step -StepNum 3 `
    -Title "Proof-of-Work Mining Benchmark across 3 Targets" `
    -Speech "Next, we run the CPU mining benchmark across three toy difficulty targets. The observed attempts match geometric distribution expectations, confirming the correctness of our nonce search." `
    -Command "$PYTHON -m chain.cli benchmark"

# STEP 4
Prompt-Step -StepNum 4 `
    -Title "Two-Miner Fork Simulation & Cumulative Work Reorganisation" `
    -Speech "Now we simulate two miners competing on a fork. Miner B produces a block with 4x higher difficulty. The chain manager detects higher cumulative work and reorganises to Branch B automatically." `
    -Command "$PYTHON -m chain.cli simulate-fork"

# STEP 5
Prompt-Step -StepNum 5 `
    -Title "Automated Test Suite Verification" `
    -Speech "Finally, we run the automated pytest test suite. All 11 unit tests pass covering header serialization, PoW verification, reorganisation rollbacks, and orphan handling. Thank you!" `
    -Command "$PYTHON -m pytest -v"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO FOR ASSIGNMENT 5 COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [ENTER] to exit runner..."
