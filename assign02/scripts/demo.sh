#!/usr/bin/env bash
# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 2 (merkle)
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
echo " ASSIGNMENT 2: Merkle Trees and Proofs of Inclusion (merkle)"
echo " Student: Navaneeth Nalla | Roll: 2301AI14"
echo "================================================================================"

EXPECTED_ROOT=$($PYTHON -c "from merkle.core import MerkleTree; t = MerkleTree([f'tx{i}'.encode() for i in range(1,6)]); print(t.root_hex)")

run_step "$PYTHON -m merkle.cli --help"
run_step "$PYTHON -m merkle.cli root \"tx1\" \"tx2\" \"tx3\" \"tx4\" \"tx5\""
run_step "$PYTHON -m merkle.cli prove --index 2 \"tx1\" \"tx2\" \"tx3\" \"tx4\" \"tx5\" --out proof.json"
run_step "$PYTHON -m merkle.cli verify --leaf \"tx3\" --proof proof.json --root $EXPECTED_ROOT"
run_step "$PYTHON -m merkle.cli verify --leaf \"tx3_tampered\" --proof proof.json --root $EXPECTED_ROOT || true"
run_step "$PYTHON -m merkle.cli benchmark"
run_step "$PYTHON -m pytest -v"

echo ""
echo "================================================================================"
echo " DEMO COMPLETE - ALL TESTS PASS"
echo "================================================================================"
