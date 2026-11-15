#!/usr/bin/env bash
# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 5 (chain)
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
echo -e "\033[1;33m VIDEO RECORDING RUNNER: ASSIGNMENT 5 (chain)\033[0m"
echo " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in"
echo "================================================================================"
echo ""

step 1 "Introduction" \
    "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 5: Blocks, Proof of Work, Forks, and Reorganisation using the 'chain' tool." \
    "$PYTHON -m chain.cli --help"

step 2 "Canonical 116-Byte Block Header Binary Format" \
    "Here we inspect the annotated 116-byte binary block header format: version, previous block hash, Merkle root, timestamp, target, and nonce. Double-SHA256 of these bytes forms the block hash." \
    "$PYTHON -m chain.cli hex-dump"

step 3 "Proof-of-Work Mining Benchmark across 3 Targets" \
    "Next, we run the CPU mining benchmark across three toy difficulty targets. The observed attempts match geometric distribution expectations, confirming the correctness of our nonce search." \
    "$PYTHON -m chain.cli benchmark"

step 4 "Two-Miner Fork Simulation & Cumulative Work Reorganisation" \
    "Now we simulate two miners competing on a fork. Miner B produces a block with 4x higher difficulty. The chain manager detects higher cumulative work and reorganises to Branch B automatically." \
    "$PYTHON -m chain.cli simulate-fork"

step 5 "Automated Test Suite Verification" \
    "Finally, we run the automated pytest test suite. All 11 unit tests pass covering header serialization, PoW verification, reorganisation rollbacks, and orphan handling. Thank you!" \
    "$PYTHON -m pytest -v"

echo "================================================================================"
echo " DEMO FOR ASSIGNMENT 5 COMPLETED! "
echo "================================================================================"
