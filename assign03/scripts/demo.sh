#!/usr/bin/env bash
# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 3 (wallet)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON="python"
if command -v python3 &>/dev/null; then
    PYTHON="python3"
fi

step() {
    echo "--------------------------------------------------------------------------------"
    echo -e "\033[1;33m[STEP $1] $2\033[0m"
    echo "--------------------------------------------------------------------------------"
    echo -e "\033[1;36m[SAY THIS ALOUD]:\033[0m"
    echo "$3"
    echo ""
    echo -e "\033[1;30m[COMMAND]: $4\033[0m"
    read -p ">>> Press [ENTER] to execute command..."
    eval "$4"
    echo ""
}

clear
echo "================================================================================"
echo -e "\033[1;33m VIDEO RECORDING RUNNER: ASSIGNMENT 3 (wallet)\033[0m"
echo " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in"
echo "================================================================================"
echo ""

rm -f dev.key pub.json sample_tx.json signed_tx.json state.json tampered_tx.json

step 1 "Introduction" \
    "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 3: Keys, Addresses, and Signed Transactions using the 'wallet' tool." \
    "$PYTHON -m wallet.cli --help"

step 2 "Keypair Generation & Base58Check Address Derivation" \
    "First, we run 'keygen' to generate an Ed25519 keypair. The private key is saved to dev.key with testnet warning and restricted permissions. The public key and derived address are saved to pub.json." \
    "$PYTHON -m wallet.cli keygen --out dev.key --pub-out pub.json && cat pub.json"

PUBKEY=$($PYTHON -c "import json; print(json.load(open('pub.json'))['public_key_hex'])")
ADDR=$($PYTHON -c "import json; print(json.load(open('pub.json'))['address'])")

$PYTHON -c "import json; json.dump({'version': 1, 'network_id': 'course-testnet', 'sender': '$ADDR', 'recipient': 'mgJ4iHqTq5hR5zV4eS9Q6Yx3u8a2K1p7Xy', 'amount_units': 1250000, 'nonce': 1, 'memo_hash': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, open('sample_tx.json', 'w'))"

step 3 "Independent Address Derivation from Public Key" \
    "Here we verify that address derivation is deterministic by passing the raw public key to the 'address' command. It computes the exact same Base58Check address." \
    "$PYTHON -m wallet.cli address $PUBKEY"

step 4 "Canonical Transaction Signing" \
    "Now we sign our transaction paying 1,250,000 units to Bob. The wallet canonicalizes the JSON according to RFC-8785 and generates an Ed25519 signature." \
    "$PYTHON -m wallet.cli sign --key dev.key --tx sample_tx.json --out signed_tx.json && cat signed_tx.json"

step 5 "Independent Signature & Nonce Verification" \
    "Next, an independent node verifies the signature, sender address, and nonce. Notice: TRANSACTION VERIFIED! Everything matches authentic state." \
    "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json"

$PYTHON -c "import json; d = json.load(open('signed_tx.json')); d['tx']['amount_units'] = 9999999; json.dump(d, open('tampered_tx.json', 'w'))"

step 6 "Tamper Detection: Rejecting Modified Amount" \
    "What happens if an attacker modifies the payment amount from 1,250,000 to 9,999,999 units? The cryptographic signature check immediately detects tampering and rejects it." \
    "$PYTHON -m wallet.cli verify --signed-tx tampered_tx.json || true"

step 7 "Replay Attack Prevention via Nonce Tracking" \
    "What if an attacker tries to re-submit the same transaction to spend funds a second time? The state database tracks nonces and rejects the replayed nonce." \
    "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json || true"

step 8 "Automated Test Suite Verification" \
    "Finally, we run the automated test suite. All 14 unit tests pass with a 100 percent pass rate. Thank you!" \
    "$PYTHON -m pytest -v"

echo "================================================================================"
echo " DEMO FOR ASSIGNMENT 3 COMPLETED! "
echo "================================================================================"
