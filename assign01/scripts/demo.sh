#!/usr/bin/env bash
# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 1 (hashlab)
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
echo -e "\033[1;33m VIDEO RECORDING RUNNER: ASSIGNMENT 1 (hashlab)\033[0m"
echo " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in"
echo "================================================================================"
echo ""

step 1 "Introduction" \
    "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14, from IIT Patna. Today I am presenting Assignment 1: Bytes, Hashes, and Reproducible Data using my CLI tool 'hashlab'." \
    "$PYTHON -m hashlab.cli --help"

step 2 "Basic Text Hashing & Output Diagnostics" \
    "Here we run the 'text' mode on the string 'Alice pays Bob 10'. The tool outputs the byte count of 18 bytes, the SHA-256 digest in hex, and in Base64." \
    "$PYTHON -m hashlab.cli text \"Alice pays Bob 10\""

step 3 "Hex Mode Parsing & Malformed Hex Rejection" \
    "In hex mode, valid hex '0102030405' decodes to 5 raw bytes. An invalid hex string '010203040z' is rejected safely with a diagnostic error." \
    "$PYTHON -m hashlab.cli hex \"0102030405\"; echo '--- Testing Malformed Hex Rejection ---'; $PYTHON -m hashlab.cli hex \"010203040z\" || true"

step 4 "Avalanche Effect & Hamming Distance" \
    "Now we test the Avalanche effect. By flipping just bit 7 in the input string, we measure the Hamming distance between digests. Notice that approximately 128 out of 256 bits changed, demonstrating ideal cryptographic diffusion." \
    "$PYTHON -m hashlab.cli avalanche --text \"Alice pays Bob 10\" --bit 7"

step 5 "Canonical JSON Deterministic Serialization" \
    "In blockchains, transactions require canonical JSON serialization. Our canonical-json mode sorts keys, removes whitespace, and normalizes characters into deterministic bytes." \
    "$PYTHON -m hashlab.cli canonical-json '{\"recipient\":\"Bob\",\"amount\":10}'"

step 6 "Visual Differences & Hash Sensitivity" \
    "This demo shows why visual similarity is deceptive: line endings, Unicode NFC versus NFD, integer versus string, and raw key orders produce different hashes, but canonical JSON resolves ambiguity." \
    "$PYTHON -m hashlab.cli demo-differences"

step 7 "Automated Unit Test Suite Verification" \
    "Finally, we run the automated pytest test suite to verify all acceptance criteria and test vectors. All 19 tests pass cleanly. Thank you!" \
    "$PYTHON -m pytest -v"

echo "================================================================================"
echo " DEMO FOR ASSIGNMENT 1 COMPLETED! "
echo "================================================================================"
