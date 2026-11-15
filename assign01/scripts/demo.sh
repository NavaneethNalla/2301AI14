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

run_step() {
    echo ""
    read -p "Press [Enter] to run..."
    echo -e "\033[1;36m$ $1\033[0m"
    eval "$1"
}

clear
echo "================================================================================"
echo " ASSIGNMENT 1: Bytes, Hashes, and Reproducible Data (hashlab)"
echo " Student: Navaneeth Nalla | Roll: 2301AI14"
echo "================================================================================"

run_step "$PYTHON -m hashlab.cli --help"
run_step "$PYTHON -m hashlab.cli text \"Alice pays Bob 10\""
run_step "$PYTHON -m hashlab.cli hex \"0102030405\""
run_step "$PYTHON -m hashlab.cli hex \"010203040z\" || true"
run_step "$PYTHON -m hashlab.cli avalanche --text \"Alice pays Bob 10\" --bit 7"
run_step "$PYTHON -m hashlab.cli canonical-json '{\"recipient\":\"Bob\",\"amount\":10}'"
run_step "$PYTHON -m hashlab.cli demo-differences"
run_step "$PYTHON -m pytest -v"

echo ""
echo "================================================================================"
echo " DEMO COMPLETE - ALL TESTS PASS"
echo "================================================================================"
