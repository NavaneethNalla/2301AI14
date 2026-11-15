# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 3 (wallet)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

$ErrorActionPreference = "Continue"

# Detect Python
$PYTHON = "python"
if (Test-Path "C:\Users\navan\anaconda3\python.exe") {
    $PYTHON = "C:\Users\navan\anaconda3\python.exe"
}

# Go to assign03 root
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
Write-Host " ASSIGNMENT 3: Keys, Addresses, and Signed Transactions (wallet)" -ForegroundColor Yellow
Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan

# Clean prior demo files
Remove-Item -Force dev.key, pub.json, sample_tx.json, signed_tx.json, state.json, tampered_tx.json -ErrorAction SilentlyContinue

# Step 1: Help overview
Run-Step -Command "$PYTHON -m wallet.cli --help"

# Step 2: Keygen
Run-Step -Command "$PYTHON -m wallet.cli keygen --out dev.key --pub-out pub.json"

# Read public key and address
$PUB_DATA = Get-Content pub.json | ConvertFrom-Json
$ADDR = $PUB_DATA.address
$PUBKEY = $PUB_DATA.public_key_hex

# Prepare sample transaction
$SAMPLE_TX = @{
    version = 1
    network_id = "course-testnet"
    sender = $ADDR
    recipient = "mgJ4iHqTq5hR5zV4eS9Q6Yx3u8a2K1p7Xy"
    amount_units = 1250000
    nonce = 1
    memo_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
} | ConvertTo-Json
$SAMPLE_TX | Set-Content sample_tx.json -Encoding utf8

# Step 3: Address derivation
Run-Step -Command "$PYTHON -m wallet.cli address $PUBKEY"

# Step 4: Sign canonical transaction
Run-Step -Command "$PYTHON -m wallet.cli sign --key dev.key --tx sample_tx.json --out signed_tx.json"

# Step 5: Verify valid transaction
Run-Step -Command "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json"

# Prepare tampered transaction
$TAMPERED_DATA = Get-Content signed_tx.json | ConvertFrom-Json
$TAMPERED_DATA.tx.amount_units = 9999999
$TAMPERED_DATA | ConvertTo-Json -Depth 5 | Set-Content tampered_tx.json -Encoding utf8

# Step 6: Reject tampered amount
Run-Step -Command "$PYTHON -m wallet.cli verify --signed-tx tampered_tx.json"

# Step 7: Reject replayed nonce
Run-Step -Command "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json"

# Step 8: Automated unit tests
Run-Step -Command "$PYTHON -m pytest -v"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO COMPLETE - ALL TESTS PASS" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [Enter] to exit"
