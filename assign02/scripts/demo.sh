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
echo -e "\033[1;33m VIDEO RECORDING RUNNER: ASSIGNMENT 2 (merkle)\033[0m"
echo " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in"
echo "================================================================================"
echo ""

EXPECTED_ROOT=$($PYTHON -c "from merkle.core import MerkleTree; t = MerkleTree([f'tx{i}'.encode() for i in range(1,6)]); print(t.root_hex)")

step 1 "Introduction" \
    "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 2: Merkle Trees and Proofs of Inclusion." \
    "$PYTHON -m merkle.cli --help"

step 2 "Computing Merkle Root with Domain Separation & Odd Leaf Promotion" \
    "Here we compute the Merkle root for 5 transactions. Notice domain separation: leaves use prefix 0x00 and internal nodes 0x01. Odd leaf 5 is promoted directly without duplicate hashing." \
    "$PYTHON -m merkle.cli root \"tx1\" \"tx2\" \"tx3\" \"tx4\" \"tx5\""

step 3 "Generating Inclusion Proof for Leaf Index 2 ('tx3')" \
    "Next, we generate an inclusion proof for leaf index 2, which corresponds to tx3. The proof contains the tree size, leaf index, and the cryptographic sibling path formatted in JSON." \
    "$PYTHON -m merkle.cli prove --index 2 \"tx1\" \"tx2\" \"tx3\" \"tx4\" \"tx5\" --out proof.json && cat proof.json"

step 4 "Independent Proof Verification (Authentic Leaf)" \
    "Now we verify the inclusion proof against the expected root. The verifier reconstructs parent hashes along the sibling path. As you can see, verification succeeds!" \
    "$PYTHON -m merkle.cli verify --leaf \"tx3\" --proof proof.json --root $EXPECTED_ROOT"

step 5 "Tamper Resistance & Fraud Detection" \
    "If an attacker tries to verify a tampered leaf 'tx3_tampered' with the same proof, the tool immediately detects the hash mismatch and rejects the proof." \
    "$PYTHON -m merkle.cli verify --leaf \"tx3_tampered\" --proof proof.json --root $EXPECTED_ROOT || true"

step 6 "Performance Benchmark (8, 1,024, and 100,000 Leaves)" \
    "Now we run the benchmark across 8, 1024, and 100,000 leaves. Building a 100,000-leaf Merkle tree takes only around 0.12 seconds, and the proof requires only 17 siblings, demonstrating logarithmic scalability." \
    "$PYTHON -m merkle.cli benchmark"

step 7 "Automated Unit Test Suite Verification" \
    "Finally, we run the automated pytest verification suite. All 25 unit tests pass with 100 percent success. Thank you!" \
    "$PYTHON -m pytest -v"

echo "================================================================================"
echo " DEMO FOR ASSIGNMENT 2 COMPLETED! "
echo "================================================================================"
