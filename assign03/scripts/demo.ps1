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

function Show-Header {
    Clear-Host
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " VIDEO RECORDING RUNNER: ASSIGNMENT 3 (wallet)" -ForegroundColor Yellow
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

# Clean prior demo artifacts
Remove-Item -Force dev.key, pub.json, sample_tx.json, signed_tx.json, state.json, tampered_tx.json -ErrorAction SilentlyContinue

# STEP 1
Prompt-Step -StepNum 1 `
    -Title "Introduction" `
    -Speech "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 3: Keys, Addresses, and Signed Transactions using the 'wallet' tool." `
    -Command "$PYTHON -m wallet.cli --help"

# STEP 2
Prompt-Step -StepNum 2 `
    -Title "Keypair Generation & Base58Check Address Derivation" `
    -Speech "First, we run 'keygen' to generate an Ed25519 keypair. The private key is saved to dev.key with testnet warning and restricted permissions. The public key and derived address are saved to pub.json." `
    -Command "$PYTHON -m wallet.cli keygen --out dev.key --pub-out pub.json; Write-Host '--- Exported Public Info ---' -ForegroundColor DarkGray; Get-Content pub.json"

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

# STEP 3
Prompt-Step -StepNum 3 `
    -Title "Independent Address Derivation from Public Key" `
    -Speech "Here we verify that address derivation is deterministic by passing the raw public key to the 'address' command. It computes the exact same Base58Check address." `
    -Command "$PYTHON -m wallet.cli address $PUBKEY"

# STEP 4
Prompt-Step -StepNum 4 `
    -Title "Canonical Transaction Signing" `
    -Speech "Now we sign our transaction paying 1,250,000 units to Bob. The wallet canonicalizes the JSON according to RFC-8785 and generates an Ed25519 signature." `
    -Command "$PYTHON -m wallet.cli sign --key dev.key --tx sample_tx.json --out signed_tx.json; Write-Host '--- Signed Transaction Output ---' -ForegroundColor DarkGray; Get-Content signed_tx.json"

# STEP 5
Prompt-Step -StepNum 5 `
    -Title "Independent Signature & Nonce Verification" `
    -Speech "Next, an independent node verifies the signature, sender address, and nonce. Notice: TRANSACTION VERIFIED! Everything matches authentic state." `
    -Command "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json"

# STEP 6
$TAMPERED_DATA = Get-Content signed_tx.json | ConvertFrom-Json
$TAMPERED_DATA.tx.amount_units = 9999999
$TAMPERED_DATA | ConvertTo-Json -Depth 5 | Set-Content tampered_tx.json -Encoding utf8

Prompt-Step -StepNum 6 `
    -Title "Tamper Detection: Rejecting Modified Amount" `
    -Speech "What happens if an attacker modifies the payment amount from 1,250,000 to 9,999,999 units? The cryptographic signature check immediately detects tampering and rejects it." `
    -Command "$PYTHON -m wallet.cli verify --signed-tx tampered_tx.json"

# STEP 7
Prompt-Step -StepNum 7 `
    -Title "Replay Attack Prevention via Nonce Tracking" `
    -Speech "What if an attacker tries to re-submit the same transaction to spend funds a second time? The state database tracks nonces and rejects the replayed nonce." `
    -Command "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json"

# STEP 8
Prompt-Step -StepNum 8 `
    -Title "Automated Test Suite Verification" `
    -Speech "Finally, we run the automated test suite. All 14 unit tests pass with a 100 percent pass rate. Thank you!" `
    -Command "$PYTHON -m pytest -v"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " DEMO FOR ASSIGNMENT 3 COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Read-Host "Press [ENTER] to exit runner..."
