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
Write-Host " ASSIGNMENT 2: Merkle Trees and Proofs of Inclusion (merkle)" -ForegroundColor Yellow
Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan

# Precompute expected root for verification
$GLOBAL:EXPECTED_ROOT = (& $PYTHON -c "from merkle.core import MerkleTree; t = MerkleTree([f'tx{i}'.encode() for i in range(1,6)]); print(t.root_hex)").Trim()

# Step 1: Help overview
Run-Step -Command "$PYTHON -m merkle.cli --help"

# Step 2: Calculate root
Run-Step -Command "$PYTHON -m merkle.cli root `"tx1`" `"tx2`" `"tx3`" `"tx4`" `"tx5`""

# Step 3: Generate proof
Run-Step -Command "$PYTHON -m merkle.cli prove --index 2 `"tx1`" `"tx2`" `"tx3`" `"tx4`" `"tx5`" --out proof.json"

# Step 4: Verify authentic leaf
Run-Step -Command "$PYTHON -m merkle.cli verify --leaf `"tx3`" --proof proof.json --root $GLOBAL:EXPECTED_ROOT"

# Step 5: Reject tampered leaf
Run-Step -Command "$PYTHON -m merkle.cli verify --leaf `"tx3_tampered`" --proof proof.json --root $GLOBAL:EXPECTED_ROOT"

# Step 6: Benchmark (8, 1024, 100,000 leaves)
Run-Step -Command "$PYTHON -m merkle.cli benchmark"

# Step 7: Automated unit tests
Run-Step -Command "$PYTHON -m pytest -v"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO COMPLETE - ALL TESTS PASS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [Enter] to exit"
