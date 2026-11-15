"""
utxo.cli
========
Command-line interface and demo runner for the UTXO ledger.
Commands:
  demo-alice-bob  - Execute the canonical Alice-pays-Bob (40+70 -> 85+23) scenario with double-spend test
  inspect-ledger  - Print current UTXO set and balances from a snapshot
  validate-tx     - Validate a transaction against a ledger snapshot
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric import ed25519

from utxo.ledger import Ledger
from utxo.models import (
    OutPoint,
    Transaction,
    TxOutput,
    compute_pubkey_hash,
)


def cmd_demo_alice_bob(args: argparse.Namespace) -> int:
    print("=" * 75)
    print("UTXO LEDGER EXECUTION DEMO: ALICE PAYS BOB SCENARIO")
    print("=" * 75)

    # 1. Initialize keys for Alice and Bob
    priv_alice = ed25519.Ed25519PrivateKey.generate()
    pub_alice = priv_alice.public_key().public_bytes_raw()
    pkh_alice = compute_pubkey_hash(pub_alice)

    priv_bob = ed25519.Ed25519PrivateKey.generate()
    pub_bob = priv_bob.public_key().public_bytes_raw()
    pkh_bob = compute_pubkey_hash(pub_bob)

    print(f"Alice PubKeyHash: {pkh_alice}")
    print(f"Bob   PubKeyHash: {pkh_bob}")

    # 2. Setup initial ledger state with two UTXOs for Alice: 40 and 70 units
    ledger = Ledger()
    op_40 = OutPoint(tx_id="11" * 32, output_index=0)
    op_70 = OutPoint(tx_id="22" * 32, output_index=1)
    ledger.add_utxo(op_40, TxOutput(value=40, pubkey_hash=pkh_alice))
    ledger.add_utxo(op_70, TxOutput(value=70, pubkey_hash=pkh_alice))

    print("\n--- INITIAL UTXO LEDGER STATE ---")
    for op, out in ledger.utxos.items():
        print(f"  {op.to_str()} => value: {out.value:>3}, owner: {out.pubkey_hash}")

    # 3. Alice pays Bob 85 units with fee 2
    # Coin selection: 70 + 40 = 110. Payment: 85. Fee: 2. Change: 110 - 85 - 2 = 23.
    print("\n[ACTION 1] Alice builds and signs transaction paying 85 to Bob with fee 2...")
    tx1 = ledger.build_and_sign_transaction(
        priv_key_bytes=priv_alice.private_bytes_raw(),
        recipient_pubkey_hash=pkh_bob,
        amount=85,
        fee=2,
    )
    print(f"Transaction ID: {tx1.tx_id}")
    print(f"Inputs consumed: {[inp.outpoint.to_str() for inp in tx1.inputs]}")
    print(f"Outputs created: {[(out.value, out.pubkey_hash) for out in tx1.outputs]}")

    success1, fee1, msg1 = ledger.apply_transaction(tx1)
    print(f"Submission 1 Result: {msg1} (Fee collected: {fee1})")
    assert success1 is True

    print("\n--- UTXO LEDGER STATE AFTER TRANSACTION 1 ---")
    for op, out in ledger.utxos.items():
        owner_name = "Bob" if out.pubkey_hash == pkh_bob else "Alice (change)"
        print(f"  {op.to_str()} => value: {out.value:>3}, owner: {owner_name} ({out.pubkey_hash})")

    # 4. Attempt to submit the EXACT SAME transaction a second time (Double Spend Attack)
    print("\n[ACTION 2] Mallory re-submits the exact same transaction (Double Spend Attack)...")
    success2, fee2, msg2 = ledger.apply_transaction(tx1)
    print(f"Submission 2 Result: {msg2}")
    assert success2 is False

    print("\n--- EXECUTION TRACE ---")
    for entry in ledger.execution_trace:
        print(f"  tx_id: {entry['tx_id'][:16]}... | status: {entry['status']:<8} | reason: {entry['reason']}")

    print("=" * 75)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="utxo",
        description="In-memory UTXO Ledger and Transaction Validator CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # demo-alice-bob
    p_demo = subparsers.add_parser("demo-alice-bob", help="Run Alice-pays-Bob scenario with double-spend check.")
    p_demo.set_defaults(func=cmd_demo_alice_bob)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

