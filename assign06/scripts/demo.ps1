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

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " VIDEO RECORDING RUNNER: ASSIGNMENT 6 (p2p)" -ForegroundColor Yellow
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
    -Speech "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 6: A Peer-to-Peer Mempool and Block Relay Network using the 'p2p' package." `
    -Command "$PYTHON -m p2p.cli --help"

# STEP 2
Prompt-Step -StepNum 2 `
    -Title "5-Node Network Partition, Divergent Mining, Healing & Convergence" `
    -Speech "Now we execute the 5-node partition simulation across 4 phases: forming disconnected clusters A and B, mining divergent blocks, bridging Node 1 and Node 3 to heal the partition, and gossiping inventory until all 5 nodes converge on the winning chain tip." `
    -Command "$PYTHON -m p2p.cli simulate-partition"

# STEP 3
Prompt-Step -StepNum 3 `
    -Title "Automated Test Suite Verification" `
    -Speech "Finally, we run the automated pytest test suite using asyncio. All 10 tests pass covering message framing, rate limiting, mempool conflict handling, TTL expiration, and convergence. Thank you!" `
    -Command "$PYTHON -m pytest -v"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO FOR ASSIGNMENT 6 COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [ENTER] to exit runner..."
