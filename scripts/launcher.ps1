# ==============================================================================
# MASTER VIDEO DEMO LAUNCHER
# Course: Practical Blockchain Engineering (Dr. Mayank Agarwal, IIT Patna)
# Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in
# ==============================================================================
#
Clear-Host
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " MASTER VIDEO RECORDING DEMO LAUNCHER (IIT Patna CSE)" -ForegroundColor Yellow
Write-Host " Student: Navaneeth Nalla | Roll: 2301AI14 | Webmail: navaneeth_2301ai14@iitp.ac.in" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Select which assignment demo you want to record:" -ForegroundColor White
Write-Host "  [1] Assignment 1: hashlab (Bytes, Hashes & Reproducible Data)" -ForegroundColor Cyan
Write-Host "  [2] Assignment 2: merkle  (Merkle Trees & Proofs of Inclusion)" -ForegroundColor Cyan
Write-Host "  [3] Assignment 3: wallet  (Keys, Addresses & Signed Transactions)" -ForegroundColor Cyan
Write-Host "  [4] Assignment 4: utxo    (UTXO Ledger & Transaction Validator)" -ForegroundColor Cyan
Write-Host "  [5] Assignment 5: chain   (PoW Blockchain, Forks & Reorganisation)" -ForegroundColor Cyan
Write-Host "  [6] Assignment 6: p2p     (P2P Mempool & Block Relay Network)" -ForegroundColor Cyan
Write-Host "  [7] Assignment 7: Escrow  (Solidity Escrow Contract & Deployment)" -ForegroundColor Cyan
Write-Host "  [Q] Quit" -ForegroundColor Red
Write-Host ""

$choice = Read-Host "Enter your choice [1-7 or Q]"

switch ($choice) {
    "1" { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\assign01\scripts\demo.ps1" }
    "2" { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\assign02\scripts\demo.ps1" }
    "3" { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\assign03\scripts\demo.ps1" }
    "4" { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\assign04\scripts\demo.ps1" }
    "5" { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\assign05\scripts\demo.ps1" }
    "6" { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\assign06\scripts\demo.ps1" }
    "7" { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\assign07\scripts\demo.ps1" }
    "Q" { exit 0 }
    "q" { exit 0 }
    default { Write-Host "Invalid choice. Exiting." -ForegroundColor Red }
}
