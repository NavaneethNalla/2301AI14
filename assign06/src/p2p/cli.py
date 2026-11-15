"""
p2p.cli
=======
Command-line interface and partition simulation runner.
Commands:
  simulate-partition - Run 5-node partition, divergent mining, healing, and convergence experiment
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

from chain.manager import ChainManager, EASY_TARGET
from chain.miner import mine_block_header
from chain.models import (
    Block,
    BlockHeader,
    create_coinbase_tx,
)
from p2p.node import P2PNode


async def run_partition_experiment() -> None:
    print("=" * 80)
    print("P2P NETWORK EXPERIMENT: 5-NODE PARTITION, FORK DIVERGENCE & HEALING CONVERGENCE")
    print("=" * 80)

    # 1. Initialize 5 nodes on localhost with identical shared genesis
    shared_genesis_target = EASY_TARGET
    nodes: list[P2PNode] = []
    for i in range(1, 6):
        node = P2PNode(node_id=f"Node{i}", host="127.0.0.1", port=0)
        await node.start()
        nodes.append(node)

    print(f"Launched 5 P2P nodes on localhost ports: {[n.port for n in nodes]}")

    # 2. Partition into two disconnected clusters:
    # Cluster A: [Node1, Node2]
    # Cluster B: [Node3, Node4, Node5]
    print("\n--- PHASE 1: FORMING PARTITIONS ---")
    # Connect Node1 <-> Node2
    await nodes[0].connect_to_peer(nodes[1].host, nodes[1].port)
    print(f"Cluster A formed: [Node1:{nodes[0].port}, Node2:{nodes[1].port}]")

    # Connect Node3 <-> Node4 <-> Node5
    await nodes[2].connect_to_peer(nodes[3].host, nodes[3].port)
    await nodes[3].connect_to_peer(nodes[4].host, nodes[4].port)
    await nodes[2].connect_to_peer(nodes[4].host, nodes[4].port)
    print(f"Cluster B formed: [Node3:{nodes[2].port}, Node4:{nodes[3].port}, Node5:{nodes[4].port}]")

    await asyncio.sleep(0.2)

    # 3. Mine 1 block on Cluster A (Node1 mines Block A1, relays to Node2)
    print("\n--- PHASE 2: DIVERGENT MINING DURING NETWORK PARTITION ---")
    cb_a1 = create_coinbase_tx("1a" * 20, subsidy=50, total_fees=0, extra_data="Side A Block 1")
    h_a1, _, _ = mine_block_header(BlockHeader(
        version=1,
        prev_block_hash=nodes[0].chain.active_tip_hash,
        merkle_root=Block(None, [cb_a1]).compute_merkle_root(),
        timestamp=int(time.time()),
        target=EASY_TARGET,
        nonce=0,
    ))
    blk_a1 = Block(header=h_a1, transactions=[cb_a1])
    await nodes[0].broadcast_mined_block(blk_a1)

    await asyncio.sleep(0.5)
    print(f"Cluster A Tip: Node1={nodes[0].chain.active_tip_hash[:16]}... (Height {nodes[0].chain.active_height}) | Node2={nodes[1].chain.active_tip_hash[:16]}...")
    assert nodes[0].chain.active_tip_hash == nodes[1].chain.active_tip_hash == blk_a1.block_hash

    # 4. Mine 2 blocks on Cluster B (Higher cumulative work)
    # Block B1
    cb_b1 = create_coinbase_tx("1b" * 20, subsidy=50, total_fees=0, extra_data="Side B Block 1")
    h_b1, _, _ = mine_block_header(BlockHeader(
        version=1,
        prev_block_hash=nodes[2].chain.active_tip_hash,
        merkle_root=Block(None, [cb_b1]).compute_merkle_root(),
        timestamp=int(time.time()),
        target=EASY_TARGET,
        nonce=0,
    ))
    blk_b1 = Block(header=h_b1, transactions=[cb_b1])
    await nodes[2].broadcast_mined_block(blk_b1)
    await asyncio.sleep(0.3)

    # Block B2
    cb_b2 = create_coinbase_tx("2b" * 20, subsidy=50, total_fees=0, extra_data="Side B Block 2")
    h_b2, _, _ = mine_block_header(BlockHeader(
        version=1,
        prev_block_hash=nodes[2].chain.active_tip_hash,
        merkle_root=Block(None, [cb_b2]).compute_merkle_root(),
        timestamp=int(time.time()),
        target=EASY_TARGET,
        nonce=0,
    ))
    blk_b2 = Block(header=h_b2, transactions=[cb_b2])
    await nodes[2].broadcast_mined_block(blk_b2)
    await asyncio.sleep(0.5)

    print(f"Cluster B Tip: Node3={nodes[2].chain.active_tip_hash[:16]}... (Height {nodes[2].chain.active_height}) | Node4={nodes[3].chain.active_tip_hash[:16]}... | Node5={nodes[4].chain.active_tip_hash[:16]}...")
    assert nodes[2].chain.active_tip_hash == nodes[3].chain.active_tip_hash == nodes[4].chain.active_tip_hash == blk_b2.block_hash

    # 5. HEAL PARTITION: Connect Node1 (Cluster A) to Node3 (Cluster B)
    print("\n--- PHASE 3: HEALING PARTITION & CONVERGENCE ---")
    print("Reconnecting Cluster A to Cluster B via [Node1 <-> Node3] bridge...")
    await nodes[0].connect_to_peer(nodes[2].host, nodes[2].port)

    # Gossip the winning branch inventory from Node3 to Node1
    await nodes[2].broadcast_inventory([
        {"type": "block", "id": blk_b1.block_hash},
        {"type": "block", "id": blk_b2.block_hash},
    ])

    # Allow convergence gossip propagation across all 5 nodes
    await asyncio.sleep(1.0)

    print("\n--- PHASE 4: FINAL CONVERGENCE VERIFICATION ---")
    winning_hash = blk_b2.block_hash
    for n in nodes:
        print(f"  {n.node_id:<6} -> Active Tip: {n.chain.active_tip_hash[:16]}... | Height: {n.chain.active_height} | Work: {n.chain.active_cumulative_work}")
        assert n.chain.active_tip_hash == winning_hash, f"{n.node_id} failed to converge on winning tip!"

    print(f"\nSUCCESS: ALL 5 NODES CONVERGED ON THE WINNING MOST-WORK CHAIN TIP ({winning_hash[:16]}...)!")

    # 6. Structured Log Sample
    print("\n--- SAMPLE STRUCTURED LOGS ---")
    sample_logs = [log for log in nodes[0].structured_logs if "BLOCK" in log["event"] or "REORG" in log["event"]][:5]
    for l in sample_logs:
        print(f"  {json.dumps(l)}")

    print("=" * 80)

    # Clean shutdown
    for n in nodes:
        await n.stop()


def cmd_simulate_partition(args: argparse.Namespace) -> int:
    asyncio.run(run_partition_experiment())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="p2p", description="Peer-to-peer network CLI and simulation tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # simulate-partition
    p_sim = subparsers.add_parser("simulate-partition", help="Run 5-node partition and convergence experiment.")
    p_sim.set_defaults(func=cmd_simulate_partition)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

