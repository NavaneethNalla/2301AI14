"""
Unit and integration tests for p2p (Assignment 6).
Covers message framing, mempool mechanics, rate limiting, and 5-node partition convergence.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import pytest

from cryptography.hazmat.primitives.asymmetric import ed25519

from chain.manager import ChainManager, EASY_TARGET
from chain.miner import mine_block_header
from chain.models import (
    Block,
    BlockHeader,
    OutPoint,
    Transaction,
    TxInput,
    TxOutput,
    create_coinbase_tx,
)
from p2p.mempool import Mempool
from p2p.messages import (
    MAX_MESSAGE_SIZE,
    frame_message,
    read_framed_message,
)
from p2p.node import P2PNode
from p2p.rate_limiter import TokenBucket


# ---------------------------------------------------------------------------
# Message Framing & Length Prefix Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_message_framing_roundtrip():
    msg = {"type": "ping", "nonce": 99999}
    framed = frame_message(msg)
    assert len(framed) >= 4
    length = struct.unpack(">I", framed[:4])[0]
    assert length == len(framed) - 4

    reader = asyncio.StreamReader()
    reader.feed_data(framed)
    reader.feed_eof()

    decoded = await read_framed_message(reader)
    assert decoded == msg


@pytest.mark.asyncio
async def test_message_framing_rejects_oversized():
    # Frame declaring 2 MB size (exceeding 1 MB limit)
    oversized_length = MAX_MESSAGE_SIZE + 500
    fake_header = struct.pack(">I", oversized_length)

    reader = asyncio.StreamReader()
    reader.feed_data(fake_header)
    reader.feed_eof()

    with pytest.raises(ValueError, match="exceeds maximum allowed"):
        await read_framed_message(reader)


# ---------------------------------------------------------------------------
# Token Bucket Rate Limiter Tests
# ---------------------------------------------------------------------------

def test_token_bucket_rate_limiter():
    tb = TokenBucket(capacity=5.0, refill_rate=2.0)
    # Burst 5 allowed
    for _ in range(5):
        assert tb.allow(1.0) is True
    # 6th request rejected
    assert tb.allow(1.0) is False

    # Sleep to refill 2 tokens
    time.sleep(1.05)
    assert tb.allow(1.0) is True


# ---------------------------------------------------------------------------
# Mempool Tests: Validation, Conflicts, Fee-Rate Ordering, TTL
# ---------------------------------------------------------------------------

@pytest.fixture
def test_keys():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()
    pkh = "aa" * 20
    return priv, pub, pkh


def test_mempool_validation_and_duplicate(test_keys):
    priv, pub, pkh = test_keys
    mempool = Mempool()
    op = OutPoint(tx_id="11" * 32, output_index=0)
    utxo_set = {op: TxOutput(value=100, pubkey_hash=pkh)}

    # Construct tx
    inp = TxInput(prev_tx_id=op.tx_id, prev_out_index=op.output_index)
    out = TxOutput(value=90, pubkey_hash="bb" * 20)
    tx = Transaction(inputs=[inp], outputs=[out])
    sh = tx.compute_sighash(0)
    tx.inputs[0].signature_hex = priv.sign(sh).hex()
    # Note: P2PKH hash of pub must match pkh
    from utxo.models import compute_pubkey_hash
    real_pkh = compute_pubkey_hash(pub)
    utxo_set[op] = TxOutput(value=100, pubkey_hash=real_pkh)
    tx.inputs[0].pubkey_hex = pub.hex()

    ok, reason = mempool.add_transaction(tx, utxo_set)
    assert ok is True
    assert mempool.contains(tx.tx_id) is True

    # Duplicate rejected
    ok2, reason2 = mempool.add_transaction(tx, utxo_set)
    assert ok2 is False
    assert reason2 == "DUPLICATE_IN_MEMPOOL"


def test_mempool_double_spend_conflict_rejection(test_keys):
    priv, pub, _ = test_keys
    from utxo.models import compute_pubkey_hash
    pkh = compute_pubkey_hash(pub)
    mempool = Mempool()
    op = OutPoint(tx_id="22" * 32, output_index=0)
    utxo_set = {op: TxOutput(value=100, pubkey_hash=pkh)}

    # Tx1 spends op to Bob
    tx1 = Transaction(inputs=[TxInput(op.tx_id, op.output_index)], outputs=[TxOutput(60, "bb" * 20)])
    tx1.inputs[0].signature_hex = priv.sign(tx1.compute_sighash(0)).hex()
    tx1.inputs[0].pubkey_hex = pub.hex()
    ok1, _ = mempool.add_transaction(tx1, utxo_set)
    assert ok1 is True

    # Tx2 spends the EXACT SAME op to Charlie (unconfirmed double-spend in mempool)
    tx2 = Transaction(inputs=[TxInput(op.tx_id, op.output_index)], outputs=[TxOutput(40, "cc" * 20)])
    tx2.inputs[0].signature_hex = priv.sign(tx2.compute_sighash(0)).hex()
    tx2.inputs[0].pubkey_hex = pub.hex()
    ok2, reason2 = mempool.add_transaction(tx2, utxo_set)
    assert ok2 is False
    assert "REJECT_MEMPOOL_CONFLICT" in reason2


def test_mempool_fee_rate_ordering(test_keys):
    priv, pub, _ = test_keys
    from utxo.models import compute_pubkey_hash
    pkh = compute_pubkey_hash(pub)
    mempool = Mempool()

    op1 = OutPoint("01" * 32, 0)
    op2 = OutPoint("02" * 32, 0)
    utxo_set = {
        op1: TxOutput(value=100, pubkey_hash=pkh),
        op2: TxOutput(value=100, pubkey_hash=pkh),
    }

    # Low fee tx: fee = 100 - 95 = 5
    tx_low = Transaction(inputs=[TxInput(op1.tx_id, 0)], outputs=[TxOutput(95, "bb" * 20)])
    tx_low.inputs[0].signature_hex = priv.sign(tx_low.compute_sighash(0)).hex()
    tx_low.inputs[0].pubkey_hex = pub.hex()

    # High fee tx: fee = 100 - 50 = 50
    tx_high = Transaction(inputs=[TxInput(op2.tx_id, 0)], outputs=[TxOutput(50, "cc" * 20)])
    tx_high.inputs[0].signature_hex = priv.sign(tx_high.compute_sighash(0)).hex()
    tx_high.inputs[0].pubkey_hex = pub.hex()

    mempool.add_transaction(tx_low, utxo_set)
    mempool.add_transaction(tx_high, utxo_set)

    template = mempool.get_block_template()
    # High fee tx must come first
    assert len(template) == 2
    assert template[0].tx_id == tx_high.tx_id
    assert template[1].tx_id == tx_low.tx_id


def test_mempool_ttl_expiry(test_keys):
    priv, pub, _ = test_keys
    from utxo.models import compute_pubkey_hash
    pkh = compute_pubkey_hash(pub)
    # 0.1 second TTL
    mempool = Mempool(ttl=0.1)
    op = OutPoint("03" * 32, 0)
    utxo_set = {op: TxOutput(value=50, pubkey_hash=pkh)}

    tx = Transaction(inputs=[TxInput(op.tx_id, 0)], outputs=[TxOutput(40, "dd" * 20)])
    tx.inputs[0].signature_hex = priv.sign(tx.compute_sighash(0)).hex()
    tx.inputs[0].pubkey_hex = pub.hex()

    mempool.add_transaction(tx, utxo_set)
    assert mempool.contains(tx.tx_id) is True

    time.sleep(0.15)
    mempool.purge_expired()
    assert mempool.contains(tx.tx_id) is False


# ---------------------------------------------------------------------------
# P2P Node Integration: 2-Node Gossip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_p2p_two_node_block_and_tx_gossip():
    node1 = P2PNode(node_id="N1", host="127.0.0.1", port=0)
    node2 = P2PNode(node_id="N2", host="127.0.0.1", port=0)
    await node1.start()
    await node2.start()

    try:
        # Connect N1 -> N2
        connected = await node1.connect_to_peer(node2.host, node2.port)
        assert connected is True
        await asyncio.sleep(0.1)

        # N1 mines a block
        cb = create_coinbase_tx("11" * 20, subsidy=50, total_fees=0)
        h, _, _ = mine_block_header(BlockHeader(
            1, node1.chain.active_tip_hash, Block(None, [cb]).compute_merkle_root(), int(time.time()), EASY_TARGET, 0
        ))
        blk = Block(h, [cb])

        # N1 broadcasts block
        await node1.broadcast_mined_block(blk)
        await asyncio.sleep(0.4)

        # N2 should have received and accepted the block via inv -> getdata -> block
        assert node2.chain.active_tip_hash == blk.block_hash
        assert node2.chain.active_height == 1

        # Check structured logs
        events_n1 = [l["event"] for l in node1.structured_logs]
        events_n2 = [l["event"] for l in node2.structured_logs]
        assert "LOCAL_BLOCK_MINED" in events_n1
        assert "BLOCK_ACCEPTED" in events_n2
    finally:
        await node1.stop()
        await node2.stop()


# ---------------------------------------------------------------------------
# 5-Node Partition & Convergence Experiment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_5_node_partition_and_convergence():
    nodes = [P2PNode(node_id=f"TestNode{i}", host="127.0.0.1", port=0) for i in range(1, 6)]
    for n in nodes:
        await n.start()

    try:
        # Partition A: [0, 1]
        await nodes[0].connect_to_peer(nodes[1].host, nodes[1].port)

        # Partition B: [2, 3, 4]
        await nodes[2].connect_to_peer(nodes[3].host, nodes[3].port)
        await nodes[3].connect_to_peer(nodes[4].host, nodes[4].port)
        await asyncio.sleep(0.1)

        # Side A mines 1 block
        cb_a = create_coinbase_tx("aa" * 20, subsidy=50, total_fees=0)
        h_a, _, _ = mine_block_header(BlockHeader(1, nodes[0].chain.active_tip_hash, Block(None, [cb_a]).compute_merkle_root(), int(time.time()), EASY_TARGET, 0))
        blk_a = Block(h_a, [cb_a])
        await nodes[0].broadcast_mined_block(blk_a)
        await asyncio.sleep(0.3)
        assert nodes[0].chain.active_tip_hash == nodes[1].chain.active_tip_hash == blk_a.block_hash

        # Side B mines 2 blocks (higher work)
        cb_b1 = create_coinbase_tx("b1" * 20, subsidy=50, total_fees=0)
        h_b1, _, _ = mine_block_header(BlockHeader(1, nodes[2].chain.active_tip_hash, Block(None, [cb_b1]).compute_merkle_root(), int(time.time()), EASY_TARGET, 0))
        blk_b1 = Block(h_b1, [cb_b1])
        await nodes[2].broadcast_mined_block(blk_b1)
        await asyncio.sleep(0.2)

        cb_b2 = create_coinbase_tx("b2" * 20, subsidy=50, total_fees=0)
        h_b2, _, _ = mine_block_header(BlockHeader(1, blk_b1.block_hash, Block(None, [cb_b2]).compute_merkle_root(), int(time.time()), EASY_TARGET, 0))
        blk_b2 = Block(h_b2, [cb_b2])
        await nodes[2].broadcast_mined_block(blk_b2)
        await asyncio.sleep(0.3)
        assert nodes[2].chain.active_tip_hash == nodes[3].chain.active_tip_hash == nodes[4].chain.active_tip_hash == blk_b2.block_hash

        # HEAL PARTITION: Connect Node 0 <-> Node 2
        await nodes[0].connect_to_peer(nodes[2].host, nodes[2].port)
        # Gossip winning blocks
        await nodes[2].broadcast_inventory([{"type": "block", "id": blk_b1.block_hash}, {"type": "block", "id": blk_b2.block_hash}])
        await asyncio.sleep(0.8)

        # ALL 5 NODES MUST CONVERGE ON BLK_B2
        winning_tip = blk_b2.block_hash
        for n in nodes:
            assert n.chain.active_tip_hash == winning_tip, f"Node {n.node_id} failed to converge!"
    finally:
        for n in nodes:
            await n.stop()


# ---------------------------------------------------------------------------
# CLI Test
# ---------------------------------------------------------------------------

def test_cli_simulate_partition():
    cmd = [sys.executable, "-m", "p2p", "simulate-partition"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res.returncode == 0
    assert "ALL 5 NODES CONVERGED ON THE WINNING MOST-WORK CHAIN TIP" in res.stdout
    assert "NODE_STARTED" in res.stdout or "SAMPLE STRUCTURED LOGS" in res.stdout

