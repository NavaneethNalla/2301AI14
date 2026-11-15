"""
chain.miner
===========
Mining engine and benchmark routines for Proof of Work.
"""

from __future__ import annotations

import time
from typing import List, Tuple

from chain.models import BlockHeader


def mine_block_header(header: BlockHeader, max_attempts: int = 10_000_000) -> Tuple[BlockHeader, int, float]:
    """
    Mines a block header by incrementing nonce until:
    int(SHA256(SHA256(header))) <= target
    """
    start_time = time.perf_counter()
    target = header.target
    current_nonce = header.nonce

    attempts = 0
    while attempts < max_attempts:
        header.nonce = current_nonce
        if header.hash_int <= target:
            elapsed = time.perf_counter() - start_time
            return header, attempts + 1, elapsed
        current_nonce += 1
        attempts += 1

    elapsed = time.perf_counter() - start_time
    raise RuntimeError(f"Mining exhausted {max_attempts} attempts without finding valid PoW.")


def run_mining_benchmark(targets: List[Tuple[str, int]]) -> List[dict]:
    """
    Benchmarks hashes/second and compares expected vs observed attempts across toy targets.
    """
    results = []
    dummy_merkle = "00" * 32
    dummy_prev = "11" * 32

    for label, target in targets:
        # Expected attempts is 2**256 / target
        expected_attempts = (2**256) / target

        header = BlockHeader(
            version=1,
            prev_block_hash=dummy_prev,
            merkle_root=dummy_merkle,
            timestamp=int(time.time()),
            target=target,
            nonce=0,
        )

        mined_header, attempts, elapsed = mine_block_header(header)
        hashes_per_sec = attempts / elapsed if elapsed > 0 else float("inf")

        results.append({
            "target_label": label,
            "target_hex": f"0x{target:064x}"[:18] + "...",
            "expected_attempts": round(expected_attempts, 1),
            "observed_attempts": attempts,
            "elapsed_seconds": round(elapsed, 5),
            "hashes_per_second": round(hashes_per_sec, 2),
            "mined_hash": mined_header.hash_hex,
            "nonce": mined_header.nonce,
        })

    return results

