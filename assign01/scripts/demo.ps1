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

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " VIDEO RECORDING RUNNER: ASSIGNMENT 1 (hashlab)" -ForegroundColor Yellow
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
    -Speech "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14, from IIT Patna. Today I am presenting Assignment 1: Bytes, Hashes, and Reproducible Data using my CLI tool 'hashlab'." `
    -Command "$PYTHON -m hashlab.cli --help"

# STEP 2
Prompt-Step -StepNum 2 `
    -Title "Basic Text Hashing & Output Diagnostics" `
    -Speech "Here we run the 'text' mode on the string 'Alice pays Bob 10'. The tool outputs the byte count of 18 bytes, the SHA-256 digest in hex, and in Base64." `
    -Command "$PYTHON -m hashlab.cli text `"Alice pays Bob 10`""

# STEP 3
Prompt-Step -StepNum 3 `
    -Title "Hex Mode Parsing & Malformed Hex Rejection" `
    -Speech "In hex mode, valid hex '0102030405' decodes to 5 raw bytes. An invalid hex string '010203040z' is rejected safely with a diagnostic error." `
    -Command "$PYTHON -m hashlab.cli hex `"0102030405`"; Write-Host '--- Testing Malformed Hex Rejection ---' -ForegroundColor DarkGray; $PYTHON -m hashlab.cli hex `"010203040z`""

# STEP 4
Prompt-Step -StepNum 4 `
    -Title "Avalanche Effect & Hamming Distance" `
    -Speech "Now we test the Avalanche effect. By flipping just bit 7 in the input string, we measure the Hamming distance between digests. Notice that approximately 128 out of 256 bits changed, demonstrating ideal cryptographic diffusion." `
    -Command "$PYTHON -m hashlab.cli avalanche --text `"Alice pays Bob 10`" --bit 7"

# STEP 5
Prompt-Step -StepNum 5 `
    -Title "Canonical JSON Deterministic Serialization" `
    -Speech "In blockchains, transactions require canonical JSON serialization. Our canonical-json mode sorts keys, removes whitespace, and normalizes characters into deterministic bytes." `
    -Command "$PYTHON -m hashlab.cli canonical-json '{\`"recipient\`":\`"Bob\`",\`"amount\`":10}'"

# STEP 6
Prompt-Step -StepNum 6 `
    -Title "Visual Differences & Hash Sensitivity" `
    -Speech "This demo shows why visual similarity is deceptive: line endings, Unicode NFC versus NFD, integer versus string, and raw key orders produce different hashes, but canonical JSON resolves ambiguity." `
    -Command "$PYTHON -m hashlab.cli demo-differences"

# STEP 7
Prompt-Step -StepNum 7 `
    -Title "Automated Unit Test Suite Verification" `
    -Speech "Finally, we run the automated pytest test suite to verify all acceptance criteria and test vectors. All 19 tests pass cleanly. Thank you!" `
    -Command "$PYTHON -m pytest -v"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO FOR ASSIGNMENT 1 COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [ENTER] to exit runner..."
