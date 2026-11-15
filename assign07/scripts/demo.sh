#!/usr/bin/env bash
# ==============================================================================
# DEMO EXECUTION RUNNER: ASSIGNMENT 7 (Escrow)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

NPM="npm"

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
echo -e "\033[1;33m VIDEO RECORDING RUNNER: ASSIGNMENT 7 (Escrow)\033[0m"
echo " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in"
echo "================================================================================"
echo ""

step 1 "Introduction" \
    "Hello everyone and Dr. Mayank Agarwal. My name is Navaneeth Nalla, roll number 2301AI14, from IIT Patna. Today I am demonstrating Assignment 7: Solidity Escrow from Specification to Deployment." \
    "cat package.json"

step 2 "Deploying Escrow Contract & End-to-End Interaction" \
    "Now we execute the automated deployment and interaction script. It deploys the Escrow contract, funds 2.0 ETH as Buyer, releases payment to Seller, executes a pull-payment withdrawal, verifies contract solvency, and logs the gas report." \
    "$NPM run deploy"

step 3 "Automated Unit & Fuzz Test Suite Verification" \
    "Finally, we run the automated Hardhat test suite. All 23 unit and fuzz tests pass covering every state transition, access control rejection, and pull withdrawal. Thank you!" \
    "$NPM test"

echo "================================================================================"
echo " DEMO FOR ASSIGNMENT 7 COMPLETED! "
echo "================================================================================"
