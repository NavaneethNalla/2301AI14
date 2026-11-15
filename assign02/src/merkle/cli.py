"""
merkle.cli
==========
Command-line interface for the Merkle tree library.
Provides commands:
  root      - Compute root hash of leaves
  prove     - Generate inclusion proof JSON for a leaf index
  verify    - Verify inclusion proof against leaf data and expected root
  benchmark - Benchmark construction time and proof sizes (8, 1024, 100000 leaves)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import List

from merkle.core import MerkleTree, verify_proof


def load_leaves(args: argparse.Namespace) -> List[bytes]:
    """Loads leaf byte sequences from either command line arguments or a text file."""
    if hasattr(args, "file") and args.file:
        path = Path(args.file)
        if not path.is_file():
            raise FileNotFoundError(f"Leaf file not found: {args.file}")
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\r\n").encode("utf-8") for line in f if line.rstrip("\r\n")]
        return lines
    elif hasattr(args, "leaves") and args.leaves:
        return [leaf.encode("utf-8") for leaf in args.leaves]
    else:
        return []


def cmd_root(args: argparse.Namespace) -> int:
    leaves = load_leaves(args)
    tree = MerkleTree(leaves)
    print(f"tree_size: {len(leaves)}")
    print(f"root: {tree.root_hex}")
    return 0


def cmd_prove(args: argparse.Namespace) -> int:
    leaves = load_leaves(args)
    if not leaves:
        print("Error: Cannot generate inclusion proof for an empty tree.", file=sys.stderr)
        return 1
    if args.index < 0 or args.index >= len(leaves):
        print(f"Error: index {args.index} out of range (tree size {len(leaves)}).", file=sys.stderr)
        return 1

    tree = MerkleTree(leaves)
    proof = tree.get_proof(args.index)
    output_json = json.dumps(proof, indent=2)
    print(output_json)
    if args.out:
        Path(args.out).write_text(output_json, encoding="utf-8")
        print(f"Proof written to {args.out}", file=sys.stderr)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    # 1. Parse proof
    proof_str = args.proof
    proof_path = Path(args.proof)
    if proof_path.is_file():
        proof_str = proof_path.read_text(encoding="utf-8")

    try:
        proof_data = json.loads(proof_str)
    except Exception as e:
        print(f"Error parsing proof JSON: {e}", file=sys.stderr)
        return 1

    leaf_bytes = args.leaf.encode("utf-8")
    try:
        is_valid = verify_proof(leaf_bytes, proof_data, args.root)
        if is_valid:
            print("VERIFICATION SUCCESS: Leaf is authentically included in the Merkle root.")
            return 0
        else:
            print("VERIFICATION FAILURE: Computed root does not match expected root.", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"VERIFICATION ERROR: {e}", file=sys.stderr)
        return 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    sizes = [8, 1024, 100_000]
    print("=" * 75)
    print("MERKLE TREE BENCHMARK PERFORMANCE REPORT")
    print("=" * 75)
    print(f"{'Leaf Count':<12} | {'Build Time (s)':<16} | {'Proof Siblings':<16} | {'Proof Size (bytes)':<18}")
    print("-" * 75)

    for n in sizes:
        leaves = [f"tx_{i:08x}".encode("ascii") for i in range(n)]

        t0 = time.perf_counter()
        tree = MerkleTree(leaves)
        build_time = time.perf_counter() - t0

        # Sample proof for middle index
        mid_idx = n // 2
        proof = tree.get_proof(mid_idx)
        sibling_count = len(proof["siblings"])
        proof_bytes_len = len(json.dumps(proof).encode("utf-8"))

        print(f"{n:<12} | {build_time:<16.6f} | {sibling_count:<16} | {proof_bytes_len:<18}")

    print("=" * 75)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="merkle",
        description="Merkle tree construction, proof generation, and verification CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # root
    p_root = subparsers.add_parser("root", help="Calculate Merkle root.")
    p_root.add_argument("leaves", nargs="*", help="Leaf strings")
    p_root.add_argument("--file", help="Path to text file containing one leaf per line")
    p_root.set_defaults(func=cmd_root)

    # prove
    p_prove = subparsers.add_parser("prove", help="Generate inclusion proof.")
    p_prove.add_argument("--index", type=int, required=True, help="0-indexed leaf index")
    p_prove.add_argument("leaves", nargs="*", help="Leaf strings")
    p_prove.add_argument("--file", help="Path to text file containing leaves")
    p_prove.add_argument("--out", help="Optional output JSON file")
    p_prove.set_defaults(func=cmd_prove)

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify inclusion proof.")
    p_verify.add_argument("--leaf", required=True, help="Original leaf string")
    p_verify.add_argument("--proof", required=True, help="Proof JSON string or file path")
    p_verify.add_argument("--root", required=True, help="Expected 64-character root hex")
    p_verify.set_defaults(func=cmd_verify)

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Run benchmark across 8, 1024, and 100,000 leaves")
    p_bench.set_defaults(func=cmd_benchmark)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

