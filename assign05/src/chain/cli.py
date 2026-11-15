"""
chain.cli
=========
Command-line interface and simulation tool for blockchain and PoW consensus.
Commands:
  benchmark     - Measure hashes/sec and expected vs observed attempts across 3 toy targets
  hex-dump      - Display annotated hex dump of an authentic 116-byte block header
  simulate-fork - Simulate two miners competing on a fork and reorganisation to the winning branch
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from chain.manager import ChainManager, EASY_TARGET
from chain.miner import mine_block_header, run_mining_benchmark
from chain.models import Block, BlockHeader, create_coinbase_tx


def cmd_hex_dump(args: argparse.Namespace) -> int:
    header = BlockHeader(
        version=1,
        prev_block_hash="00" * 32,
        merkle_root="c89ddf3c95e1e5ea01ff0fbe3aa70183eeeaee1bf6114eb31d6f30e6a88b56d3",
        timestamp=1700000000,
        target=EASY_TARGET,
        nonce=42,
    )
    raw = header.serialize()

    print("=" * 75)
    print("ANNOTATED BLOCK HEADER HEX DUMP (Total: 116 bytes)")
    print("=" * 75)
    print(f"Version (4 bytes):         {raw[:4].hex()}  (v{header.version})")
    print(f"Prev Block Hash (32 bytes): {raw[4:36].hex()}")
    print(f"Merkle Root (32 bytes):     {raw[36:68].hex()}")
    print(f"Timestamp (8 bytes):       {raw[68:76].hex()}  ({header.timestamp}s)")
    print(f"Target (32 bytes):          {raw[76:108].hex()}")
    print(f"Nonce (8 bytes):           {raw[108:116].hex()}  (nonce={header.nonce})")
    print("-" * 75)
    print(f"Full Header Hex:\n{raw.hex()}")
    print("-" * 75)
    print(f"Double-SHA256 Digest:\n{header.hash_hex}")
    print("=" * 75)
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    # 3 Toy targets:
    # Target 1: 8 leading zero bits (easy, expected ~256 attempts)
    # Target 2: 12 leading zero bits (medium, expected ~4096 attempts)
    # Target 3: 16 leading zero bits (harder, expected ~65536 attempts)
    targets = [
        ("8 leading 0-bits (Easy)", (1 << 248) - 1),
        ("12 leading 0-bits (Medium)", (1 << 244) - 1),
        ("15 leading 0-bits (Target)", (1 << 241) - 1),
    ]

    print("=" * 85)
    print("PROOF OF WORK MINING BENCHMARK REPORT")
    print("=" * 85)
    print(f"{'Target Name':<28} | {'Exp Attempts':<13} | {'Obs Attempts':<13} | {'Time (s)':<10} | {'Hashes/sec':<12}")
    print("-" * 85)

    results = run_mining_benchmark(targets)
    for r in results:
        print(f"{r['target_label']:<28} | {r['expected_attempts']:<13} | {r['observed_attempts']:<13} | {r['elapsed_seconds']:<10} | {r['hashes_per_second']:<12}")

    print("=" * 85)
    return 0


def cmd_simulate_fork(args: argparse.Namespace) -> int:
    print("=" * 75)
    print("SIMULATION: TWO MINERS CREATING AND RESOLVING A BLOCKCHAIN FORK")
    print("=" * 75)

    cm = ChainManager(genesis_target=EASY_TARGET)
    g_hash = cm.active_tip_hash
    print(f"Genesis Block mined: {g_hash[:16]}... (Height 0, Work: {cm.active_cumulative_work})")

    # 1. Miner A mines Block 1A on top of Genesis at standard target
    target_a = EASY_TARGET
    cb_a = create_coinbase_tx("aa" * 20, subsidy=50, total_fees=0, extra_data="Miner A Block 1A")
    blk_1a_header = BlockHeader(
        version=1,
        prev_block_hash=g_hash,
        merkle_root=Block(header=None, transactions=[cb_a]).compute_merkle_root(),
        timestamp=int(time.time()),
        target=target_a,
        nonce=0,
    )
    mined_1a_header, _, _ = mine_block_header(blk_1a_header)
    blk_1a = Block(header=mined_1a_header, transactions=[cb_a])
    ok_a, msg_a = cm.add_block(blk_1a)
    print(f"\n[Miner A] Mined Block 1A: {blk_1a.block_hash[:16]}... | Status: {msg_a}")
    print(f"Active Tip: {cm.active_tip_hash[:16]}... (Cumulative Work: {cm.active_cumulative_work})")

    # 2. Miner B also mined on top of Genesis, creating a FORK (Block 1B)
    # Miner B mined at a HARDER difficulty (lower target, thus HIGHER work per block!)
    target_b = EASY_TARGET >> 2  # 4x higher work
    cb_b = create_coinbase_tx("bb" * 20, subsidy=50, total_fees=0, extra_data="Miner B Block 1B (High Work)")
    blk_1b_header = BlockHeader(
        version=1,
        prev_block_hash=g_hash,
        merkle_root=Block(header=None, transactions=[cb_b]).compute_merkle_root(),
        timestamp=int(time.time()),
        target=target_b,
        nonce=0,
    )
    mined_1b_header, _, _ = mine_block_header(blk_1b_header)
    blk_1b = Block(header=mined_1b_header, transactions=[cb_b])

    print(f"\n[Miner B] Mined competing Block 1B on Genesis with 4x Difficulty...")
    print(f"Block 1B Work: {blk_1b_header.work} vs Block 1A Work: {blk_1a_header.work}")

    ok_b, msg_b = cm.add_block(blk_1b)
    print(f"Submission of Block 1B Result: {msg_b}")
    print(f"New Active Tip: {cm.active_tip_hash[:16]}... (Cumulative Work: {cm.active_cumulative_work})")

    assert cm.active_tip_hash == blk_1b.block_hash
    print("\nSUCCESS: Fork resolved in favor of the branch with the MOST cumulative work!")
    print("=" * 75)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chain", description="Blockchain consensus and PoW CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # benchmark
    p_b = subparsers.add_parser("benchmark", help="Run mining benchmark across 3 targets.")
    p_b.set_defaults(func=cmd_benchmark)

    # hex-dump
    p_h = subparsers.add_parser("hex-dump", help="Dump annotated block header hex.")
    p_h.set_defaults(func=cmd_hex_dump)

    # simulate-fork
    p_f = subparsers.add_parser("simulate-fork", help="Simulate 2-miner fork and reorganisation.")
    p_f.set_defaults(func=cmd_simulate_fork)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

