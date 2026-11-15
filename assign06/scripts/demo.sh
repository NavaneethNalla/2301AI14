#!/usr/bin/env bash
# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 6 (p2p)
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
echo -e "\033[1;33m VIDEO RECORDING RUNNER: ASSIGNMENT 6 (p2p)\033[0m"
echo " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in"
echo "================================================================================"
echo ""

step 1 "Introduction" \
    "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14. Today I am demonstrating Assignment 6: A Peer-to-Peer Mempool and Block Relay Network using the 'p2p' package." \
    "$PYTHON -m p2p.cli --help"

step 2 "5-Node Network Partition, Divergent Mining, Healing & Convergence" \
    "Now we execute the 5-node partition simulation across 4 phases: forming disconnected clusters A and B, mining divergent blocks, bridging Node 1 and Node 3 to heal the partition, and gossiping inventory until all 5 nodes converge on the winning chain tip." \
    "$PYTHON -m p2p.cli simulate-partition"

step 3 "Automated Test Suite Verification" \
    "Finally, we run the automated pytest test suite using asyncio. All 10 tests pass covering message framing, rate limiting, mempool conflict handling, TTL expiration, and convergence. Thank you!" \
    "$PYTHON -m pytest -v"

echo "================================================================================"
echo " DEMO FOR ASSIGNMENT 6 COMPLETED! "
echo "================================================================================"
