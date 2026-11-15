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

run_step() {
    echo ""
    read -p "Press [Enter] to run..."
    echo -e "\033[1;36m$ $1\033[0m"
    eval "$1"
}

clear
echo "================================================================================"
echo " ASSIGNMENT 3: Keys, Addresses, and Signed Transactions (wallet)"
echo " Student: Navaneeth Nalla | Roll: 2301AI14"
echo "================================================================================"

rm -f dev.key pub.json sample_tx.json signed_tx.json state.json tampered_tx.json

run_step "$PYTHON -m wallet.cli --help"
run_step "$PYTHON -m wallet.cli keygen --out dev.key --pub-out pub.json"

PUBKEY=$($PYTHON -c "import json; print(json.load(open('pub.json'))['public_key_hex'])")
ADDR=$($PYTHON -c "import json; print(json.load(open('pub.json'))['address'])")

$PYTHON -c "import json; json.dump({'version': 1, 'network_id': 'course-testnet', 'sender': '$ADDR', 'recipient': 'mgJ4iHqTq5hR5zV4eS9Q6Yx3u8a2K1p7Xy', 'amount_units': 1250000, 'nonce': 1, 'memo_hash': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, open('sample_tx.json', 'w'))"

run_step "$PYTHON -m wallet.cli address $PUBKEY"
run_step "$PYTHON -m wallet.cli sign --key dev.key --tx sample_tx.json --out signed_tx.json"
run_step "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json"

$PYTHON -c "import json; d = json.load(open('signed_tx.json')); d['tx']['amount_units'] = 9999999; json.dump(d, open('tampered_tx.json', 'w'))"

run_step "$PYTHON -m wallet.cli verify --signed-tx tampered_tx.json || true"
run_step "$PYTHON -m wallet.cli verify --signed-tx signed_tx.json --state-db state.json || true"
run_step "$PYTHON -m pytest -v"

echo ""
echo "================================================================================"
echo " DEMO COMPLETE - ALL TESTS PASS"
echo "================================================================================"
