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

run_step() {
    echo ""
    read -p "Press [Enter] to run..."
    echo -e "\033[1;36m$ $1\033[0m"
    eval "$1"
}

clear
echo "================================================================================"
echo " ASSIGNMENT 5: Blocks, Proof of Work, Forks, and Reorganisation (chain)"
echo " Student: Navaneeth Nalla | Roll: 2301AI14"
echo "================================================================================"

run_step "$PYTHON -m chain.cli --help"
run_step "$PYTHON -m chain.cli hex-dump"
run_step "$PYTHON -m chain.cli benchmark"
run_step "$PYTHON -m chain.cli simulate-fork"
run_step "$PYTHON -m pytest -v"

echo ""
echo "================================================================================"
echo " DEMO COMPLETE - ALL TESTS PASS"
echo "================================================================================"
