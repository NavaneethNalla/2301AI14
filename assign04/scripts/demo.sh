#!/usr/bin/env bash
# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 4 (utxo)
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
echo -e "\033[1;33m VIDEO RECORDING RUNNER: ASSIGNMENT 4 (utxo)\033[0m"
echo " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in"
echo "================================================================================"
echo ""

step 1 "Introduction" \
    "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 4: A UTXO Ledger and Transaction Validator using the 'utxo' tool." \
    "$PYTHON -m utxo.cli --help"

step 2 "Running Alice-Pays-Bob Scenario & Double-Spend Attack Rejection" \
    "Here we execute the canonical Alice-pays-Bob scenario: Alice consumes 40 and 70 units, pays 85 to Bob with fee 2, and receives 23 change. When the exact same transaction is submitted a second time, the ledger rejects it as a double-spend attempt." \
    "$PYTHON -m utxo.cli demo-alice-bob"

step 3 "Automated Test Suite Verification" \
    "Finally, we run the automated pytest test suite. All 22 tests pass covering P2PKH validation, coin selection, atomic rollbacks, and double-spend prevention. Thank you!" \
    "$PYTHON -m pytest -v"

echo "================================================================================"
echo " DEMO FOR ASSIGNMENT 4 COMPLETED! "
echo "================================================================================"
