"""
Unit and integration tests for chain (Assignment 5).
Covers PoW mining, Merkle commitments, coinbase rules, cumulative work selection,
and atomic chain reorganisations.
"""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest

from cryptography.hazmat.primitives.asymmetric import ed25519

from chain.manager import ChainManager, EASY_TARGET
from chain.miner import mine_block_header, run_mining_benchmark
from chain.models import (
    Block,
    BlockHeader,
    OutPoint,
    Transaction,
    TxInput,
    TxOutput,
    compute_merkle_root_of_hashes,
    create_coinbase_tx,
)


# ---------------------------------------------------------------------------
# Header Serialization and Mining
# ---------------------------------------------------------------------------

def test_header_serialization_roundtrip():
    header = BlockHeader(
        version=1,
        prev_block_hash="11" * 32,
        merkle_root="22" * 32,
        timestamp=1700000000,
        target=EASY_TARGET,
        nonce=12345,
    )
    raw = header.serialize()
    assert len(raw) == 116

    recovered = BlockHeader.deserialize(raw)
    assert recovered.version == header.version
    assert recovered.prev_block_hash == header.prev_block_hash
    assert recovered.merkle_root == header.merkle_root
    assert recovered.timestamp == header.timestamp
    assert recovered.target == header.target
    assert recovered.nonce == header.nonce
    assert recovered.hash_hex == header.hash_hex


def test_mine_block_finds_valid_pow():
    target = (1 << 248) - 1  # 8 leading zeros
    header = BlockHeader(
        version=1,
        prev_block_hash="aa" * 32,
        merkle_root="bb" * 32,
        timestamp=int(time.time()),
        target=target,
        nonce=0,
    )
    mined_header, attempts, elapsed = mine_block_header(header)
    assert mined_header.hash_int <= target
    assert attempts >= 1
    assert elapsed >= 0


# ---------------------------------------------------------------------------
# Block Validation Rules
# ---------------------------------------------------------------------------

def test_reject_block_invalid_pow():
    cm = ChainManager(genesis_target=EASY_TARGET)
    cb = create_coinbase_tx("11" * 20, subsidy=50, total_fees=0)
    blk = Block(
        header=BlockHeader(
            version=1,
            prev_block_hash=cm.active_tip_hash,
            merkle_root=Block(None, [cb]).compute_merkle_root(),
            timestamp=int(time.time()),
            target=EASY_TARGET,
            nonce=0,  # Unmined, high chance of hash > target
        ),
        transactions=[cb],
    )
    # Ensure nonce fails PoW
    while blk.header.hash_int <= EASY_TARGET:
        blk.header.nonce += 1
    # Mutate to guarantee failure
    blk.header.target = 1  # Near impossible target
    ok, reason = cm.add_block(blk)
    assert ok is False
    assert "REJECT_INVALID_POW" in reason


def test_reject_block_merkle_root_mismatch():
    cm = ChainManager(genesis_target=EASY_TARGET)
    cb = create_coinbase_tx("11" * 20, subsidy=50, total_fees=0)
    fake_merkle = "ff" * 32

    header = BlockHeader(
        version=1,
        prev_block_hash=cm.active_tip_hash,
        merkle_root=fake_merkle,
        timestamp=int(time.time()),
        target=EASY_TARGET,
        nonce=0,
    )
    mined_header, _, _ = mine_block_header(header)
    blk = Block(header=mined_header, transactions=[cb])

    ok, reason = cm.add_block(blk)
    assert ok is False
    assert "REJECT_MERKLE_ROOT_MISMATCH" in reason


def test_reject_excess_coinbase_reward():
    cm = ChainManager(genesis_target=EASY_TARGET)
    # Allowed subsidy is 50; try creating 100
    greedy_cb = create_coinbase_tx("11" * 20, subsidy=100, total_fees=0)

    header = BlockHeader(
        version=1,
        prev_block_hash=cm.active_tip_hash,
        merkle_root=Block(None, [greedy_cb]).compute_merkle_root(),
        timestamp=int(time.time()),
        target=EASY_TARGET,
        nonce=0,
    )
    mined_header, _, _ = mine_block_header(header)
    blk = Block(header=mined_header, transactions=[greedy_cb])

    ok, reason = cm.add_block(blk)
    assert ok is False
    assert "REJECT_EXCESS_COINBASE" in reason


def test_reject_orphan_block():
    cm = ChainManager(genesis_target=EASY_TARGET)
    cb = create_coinbase_tx("11" * 20, subsidy=50, total_fees=0)
    orphan_header = BlockHeader(
        version=1,
        prev_block_hash="99" * 32,  # Non-existent parent
        merkle_root=Block(None, [cb]).compute_merkle_root(),
        timestamp=int(time.time()),
        target=EASY_TARGET,
        nonce=0,
    )
    mined_header, _, _ = mine_block_header(orphan_header)
    blk = Block(header=mined_header, transactions=[cb])

    ok, reason = cm.add_block(blk)
    assert ok is False
    assert "REJECT_ORPHAN_BLOCK" in reason


# ---------------------------------------------------------------------------
# Cumulative Work vs Chain Length (Critical Acceptance Check)
# ---------------------------------------------------------------------------

def test_shorter_higher_work_branch_beats_longer_lower_work_branch():
    """
    CRITICAL ACCEPTANCE CHECK:
    Branch A: 2 blocks at easy target (low cumulative work).
    Branch B: 1 block at 4x harder difficulty (higher cumulative work).
    Chain must reorg to Branch B despite Branch B having fewer blocks!
    """
    cm = ChainManager(genesis_target=EASY_TARGET)
    g_hash = cm.active_tip_hash

    # Branch A: Block 1A (Easy target)
    target_easy = EASY_TARGET
    cb_1a = create_coinbase_tx("1a" * 20, subsidy=50, total_fees=0)
    h_1a = BlockHeader(1, g_hash, Block(None, [cb_1a]).compute_merkle_root(), int(time.time()), target_easy, 0)
    mined_1a, _, _ = mine_block_header(h_1a)
    blk_1a = Block(mined_1a, [cb_1a])
    ok_1a, _ = cm.add_block(blk_1a)
    assert ok_1a is True
    assert cm.active_tip_hash == blk_1a.block_hash

    # Branch A: Block 2A (Easy target) -> Length = 2, Work = W_genesis + 2 * W_easy
    cb_2a = create_coinbase_tx("2a" * 20, subsidy=50, total_fees=0)
    h_2a = BlockHeader(1, blk_1a.block_hash, Block(None, [cb_2a]).compute_merkle_root(), int(time.time()), target_easy, 0)
    mined_2a, _, _ = mine_block_header(h_2a)
    blk_2a = Block(mined_2a, [cb_2a])
    ok_2a, _ = cm.add_block(blk_2a)
    assert ok_2a is True
    assert cm.active_tip_hash == blk_2a.block_hash
    assert cm.active_height == 2

    # Branch B: Block 1B branching off Genesis, with target 8x harder (>> 2 * work of easy)
    target_hard = EASY_TARGET >> 3
    cb_1b = create_coinbase_tx("1b" * 20, subsidy=50, total_fees=0)
    h_1b = BlockHeader(1, g_hash, Block(None, [cb_1b]).compute_merkle_root(), int(time.time()), target_hard, 0)
    mined_1b, _, _ = mine_block_header(h_1b)
    blk_1b = Block(mined_1b, [cb_1b])

    # Work check
    assert blk_1b.header.work > (blk_1a.header.work + blk_2a.header.work)

    # Submitting Block 1B must trigger reorganisation: Branch B (length 1) beats Branch A (length 2)!
    ok_1b, msg_1b = cm.add_block(blk_1b)
    assert ok_1b is True
    assert "ACCEPTED_REORGANISED" in msg_1b
    assert cm.active_tip_hash == blk_1b.block_hash
    assert cm.active_height == 1  # Active tip is now at height 1 with superior cumulative work!


# ---------------------------------------------------------------------------
# Reorganisation with UTXO Restoration and Atomic Rollback
# ---------------------------------------------------------------------------

def test_reorganisation_restores_and_mutates_utxos():
    cm = ChainManager(genesis_target=EASY_TARGET)
    g_hash = cm.active_tip_hash
    g_cb_op = OutPoint(cm.block_nodes[g_hash].block.transactions[0].tx_id, 0)
    assert g_cb_op in cm.utxo_set

    # Branch A mines Block 1A
    cb_1a = create_coinbase_tx("aa" * 20, subsidy=50, total_fees=0)
    h_1a, _, _ = mine_block_header(BlockHeader(1, g_hash, Block(None, [cb_1a]).compute_merkle_root(), int(time.time()), EASY_TARGET, 0))
    blk_1a = Block(h_1a, [cb_1a])
    cm.add_block(blk_1a)

    op_1a = OutPoint(cb_1a.tx_id, 0)
    assert op_1a in cm.utxo_set

    # Branch B mines Block 1B with 4x work
    target_b = EASY_TARGET >> 2
    cb_1b = create_coinbase_tx("bb" * 20, subsidy=50, total_fees=0)
    h_1b, _, _ = mine_block_header(BlockHeader(1, g_hash, Block(None, [cb_1b]).compute_merkle_root(), int(time.time()), target_b, 0))
    blk_1b = Block(h_1b, [cb_1b])
    op_1b = OutPoint(cb_1b.tx_id, 0)

    # Apply Branch B
    cm.add_block(blk_1b)

    # After reorg:
    # 1. op_1a from disconnected branch must be REMOVED from utxo_set
    assert op_1a not in cm.utxo_set
    # 2. op_1b from connected branch must be PRESENT in utxo_set
    assert op_1b in cm.utxo_set
    # 3. Genesis UTXO still present
    assert g_cb_op in cm.utxo_set


def test_atomic_rollback_when_reorg_branch_is_invalid():
    cm = ChainManager(genesis_target=EASY_TARGET)
    g_hash = cm.active_tip_hash

    # Branch A: 1 valid block
    cb_1a = create_coinbase_tx("aa" * 20, subsidy=50, total_fees=0)
    h_1a, _, _ = mine_block_header(BlockHeader(1, g_hash, Block(None, [cb_1a]).compute_merkle_root(), int(time.time()), EASY_TARGET, 0))
    blk_1a = Block(h_1a, [cb_1a])
    cm.add_block(blk_1a)

    initial_tip = cm.active_tip_hash
    initial_utxos = dict(cm.utxo_set)

    # Branch B: Higher work block, but contains an invalid coinbase (excess reward)
    target_b = EASY_TARGET >> 2
    bad_cb_b = create_coinbase_tx("bb" * 20, subsidy=99999, total_fees=0)
    h_1b, _, _ = mine_block_header(BlockHeader(1, g_hash, Block(None, [bad_cb_b]).compute_merkle_root(), int(time.time()), target_b, 0))
    blk_1b = Block(h_1b, [bad_cb_b])

    ok, reason = cm.add_block(blk_1b)
    assert ok is False
    assert "REORG_FAILED_INVALID_BRANCH_BLOCK" in reason

    # Active chain tip and UTXO set must remain 100% UNTOUCHED
    assert cm.active_tip_hash == initial_tip
    assert cm.utxo_set == initial_utxos


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------

def test_cli_hex_dump():
    cmd = [sys.executable, "-m", "chain", "hex-dump"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res.returncode == 0
    assert "ANNOTATED BLOCK HEADER HEX DUMP" in res.stdout
    assert "Version (4 bytes):" in res.stdout


def test_cli_simulate_fork():
    cmd = [sys.executable, "-m", "chain", "simulate-fork"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res.returncode == 0
    assert "Fork resolved in favor of the branch with the MOST cumulative work" in res.stdout

