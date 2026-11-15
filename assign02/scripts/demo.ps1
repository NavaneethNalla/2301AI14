# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 2 (merkle)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

$ErrorActionPreference = "Continue"

# Detect Python
$PYTHON = "python"
if (Test-Path "C:\Users\navan\anaconda3\python.exe") {
    $PYTHON = "C:\Users\navan\anaconda3\python.exe"
}

# Go to assign02 root
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ASSIGN_DIR = Split-Path -Parent $SCRIPT_DIR
Set-Location $ASSIGN_DIR

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " VIDEO RECORDING RUNNER: ASSIGNMENT 2 (merkle)" -ForegroundColor Yellow
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

# Precompute root for verification
$GLOBAL:EXPECTED_ROOT = (& $PYTHON -c "from merkle.core import MerkleTree; t = MerkleTree([f'tx{i}'.encode() for i in range(1,6)]); print(t.root_hex)").Trim()

# STEP 1
Prompt-Step -StepNum 1 `
    -Title "Introduction" `
    -Speech "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 2: Merkle Trees and Proofs of Inclusion." `
    -Command "$PYTHON -m merkle.cli --help"

# STEP 2
Prompt-Step -StepNum 2 `
    -Title "Computing Merkle Root with Domain Separation & Odd Leaf Promotion" `
    -Speech "Here we compute the Merkle root for 5 transactions. Notice domain separation: leaves use prefix 0x00 and internal nodes 0x01. Odd leaf 5 is promoted directly without duplicate hashing." `
    -Command "$PYTHON -m merkle.cli root `"tx1`" `"tx2`" `"tx3`" `"tx4`" `"tx5`""

# STEP 3
Prompt-Step -StepNum 3 `
    -Title "Generating Inclusion Proof for Leaf Index 2 ('tx3')" `
    -Speech "Next, we generate an inclusion proof for leaf index 2, which corresponds to tx3. The proof contains the tree size, leaf index, and the cryptographic sibling path formatted in JSON." `
    -Command "$PYTHON -m merkle.cli prove --index 2 `"tx1`" `"tx2`" `"tx3`" `"tx4`" `"tx5`" --out proof.json; Write-Host '--- Saved Proof Contents ---' -ForegroundColor DarkGray; Get-Content proof.json"

# STEP 4
Prompt-Step -StepNum 4 `
    -Title "Independent Proof Verification (Authentic Leaf)" `
    -Speech "Now we verify the inclusion proof against the expected root. The verifier reconstructs parent hashes along the sibling path. As you can see, verification succeeds!" `
    -Command "$PYTHON -m merkle.cli verify --leaf `"tx3`" --proof proof.json --root $GLOBAL:EXPECTED_ROOT"

# STEP 5
Prompt-Step -StepNum 5 `
    -Title "Tamper Resistance & Fraud Detection" `
    -Speech "If an attacker tries to verify a tampered leaf 'tx3_tampered' with the same proof, the tool immediately detects the hash mismatch and rejects the proof." `
    -Command "$PYTHON -m merkle.cli verify --leaf `"tx3_tampered`" --proof proof.json --root $GLOBAL:EXPECTED_ROOT"

# STEP 6
Prompt-Step -StepNum 6 `
    -Title "Performance Benchmark (8, 1,024, and 100,000 Leaves)" `
    -Speech "Now we run the benchmark across 8, 1024, and 100,000 leaves. Building a 100,000-leaf Merkle tree takes only around 0.12 seconds, and the proof requires only 17 siblings, demonstrating logarithmic scalability." `
    -Command "$PYTHON -m merkle.cli benchmark"

# STEP 7
Prompt-Step -StepNum 7 `
    -Title "Automated Unit Test Suite Verification" `
    -Speech "Finally, we run the automated pytest verification suite. All 25 unit tests pass with 100 percent success. Thank you!" `
    -Command "$PYTHON -m pytest -v"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO FOR ASSIGNMENT 2 COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [ENTER] to exit runner..."
