"""
p2p.node
========
Asyncio-based P2P blockchain node supporting:
- Handshake, peer discovery, ping/pong keepalive
- Inventory-first gossip (inv -> getdata -> tx / block)
- Mempool synchronization and block relay
- Per-peer token-bucket rate limiting and reputation scoring
- Structured JSON logging for auditability and partition simulation
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from chain.manager import ChainManager, EASY_TARGET
from chain.models import (
    Block,
    BlockHeader,
    Transaction,
    TxInput,
    TxOutput,
    create_coinbase_tx,
)
from p2p.mempool import Mempool
from p2p.messages import (
    MAX_MESSAGE_SIZE,
    PROTOCOL_VERSION,
    frame_message,
    read_framed_message,
)
from p2p.rate_limiter import TokenBucket


class PeerConnection:
    """Manages an active TCP connection to a peer."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        peer_id: str,
        host: str,
        port: int,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.rate_limiter = TokenBucket(capacity=30.0, refill_rate=15.0)
        self.reputation: int = 100
        self.is_connected = True

    async def send(self, msg_dict: Dict[str, Any]) -> None:
        if not self.is_connected:
            return
        try:
            framed = frame_message(msg_dict)
            self.writer.write(framed)
            await self.writer.drain()
        except Exception:
            self.is_connected = False

    def close(self) -> None:
        self.is_connected = False
        try:
            self.writer.close()
        except Exception:
            pass


class P2PNode:
    """
    P2P Network Node running on localhost asyncio TCP sockets.
    """

    def __init__(
        self,
        node_id: str,
        host: str = "127.0.0.1",
        port: int = 0,
        chain_manager: Optional[ChainManager] = None,
        mempool_ttl: float = 300.0,
    ) -> None:
        self.node_id = node_id
        self.host = host
        self.port = port
        self.chain = chain_manager or ChainManager(genesis_target=EASY_TARGET)
        self.mempool = Mempool(ttl=mempool_ttl)
        self.peers: Dict[str, PeerConnection] = {}
        self.known_inventory: Set[str] = set()
        self.structured_logs: List[Dict[str, Any]] = []
        self.server: Optional[asyncio.Server] = None
        self._background_tasks: List[asyncio.Task] = []
        self.banned_peer_ids: Set[str] = set()

    def log_event(self, event: str, peer_id: str = "", object_id: str = "") -> None:
        """Records a structured JSON log entry."""
        entry = {
            "timestamp": round(time.time(), 4),
            "node_id": self.node_id,
            "peer_id": peer_id,
            "object_id": object_id,
            "event": event,
        }
        self.structured_logs.append(entry)

    async def start(self) -> None:
        """Starts the local TCP server."""
        self.server = await asyncio.start_server(self._handle_incoming, self.host, self.port)
        # Update with actual allocated port if port was 0
        if self.port == 0 and self.server.sockets:
            self.port = self.server.sockets[0].getsockname()[1]
        self.log_event("NODE_STARTED", object_id=f"{self.host}:{self.port}")

    async def stop(self) -> None:
        """Gracefully shuts down node and terminates peer sockets."""
        self.log_event("NODE_STOPPING")
        for p in list(self.peers.values()):
            p.close()
        self.peers.clear()

        for t in self._background_tasks:
            t.cancel()

        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.log_event("NODE_STOPPED")

    async def connect_to_peer(self, host: str, port: int) -> bool:
        """Establishes an outbound TCP connection to a peer."""
        try:
            reader, writer = await asyncio.open_connection(host, port)
            # Send handshake
            hs_msg = {
                "type": "handshake",
                "node_id": self.node_id,
                "listen_port": self.port,
                "best_height": self.chain.active_height,
                "best_work": self.chain.active_cumulative_work,
            }
            writer.write(frame_message(hs_msg))
            await writer.drain()

            # Read response handshake
            resp = await read_framed_message(reader)
            if not resp or resp.get("type") != "handshake":
                writer.close()
                return False

            peer_id = resp["node_id"]
            if peer_id in self.banned_peer_ids:
                writer.close()
                return False

            peer = PeerConnection(reader, writer, peer_id, host, port)
            self.peers[peer_id] = peer
            self.log_event("PEER_CONNECTED", peer_id=peer_id)

            task = asyncio.create_task(self._peer_message_loop(peer))
            self._background_tasks.append(task)
            return True
        except Exception as e:
            return False

    async def _handle_incoming(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handles incoming peer connection and handshake."""
        try:
            msg = await read_framed_message(reader)
            if not msg or msg.get("type") != "handshake":
                writer.close()
                return

            peer_id = msg["node_id"]
            if peer_id in self.banned_peer_ids:
                writer.close()
                return

            # Reply with our handshake
            reply_hs = {
                "type": "handshake",
                "node_id": self.node_id,
                "listen_port": self.port,
                "best_height": self.chain.active_height,
                "best_work": self.chain.active_cumulative_work,
            }
            writer.write(frame_message(reply_hs))
            await writer.drain()

            peer = PeerConnection(reader, writer, peer_id, "", 0)
            self.peers[peer_id] = peer
            self.log_event("PEER_ACCEPTED", peer_id=peer_id)

            await self._peer_message_loop(peer)
        except Exception:
            try:
                writer.close()
            except Exception:
                pass

    async def _peer_message_loop(self, peer: PeerConnection) -> None:
        """Continuous message dispatch loop for an active peer connection."""
        while peer.is_connected:
            try:
                # Rate limiting check
                if not peer.rate_limiter.allow():
                    peer.reputation -= 10
                    self.log_event("RATE_LIMIT_EXCEEDED", peer_id=peer.peer_id)
                    if peer.reputation <= 0:
                        self.log_event("PEER_BANNED", peer_id=peer.peer_id)
                        self.banned_peer_ids.add(peer.peer_id)
                        peer.close()
                        break
                    await asyncio.sleep(0.1)
                    continue

                msg = await read_framed_message(peer.reader)
                if msg is None:
                    break

                await self._process_message(peer, msg)
            except (ConnectionError, asyncio.IncompleteReadError):
                break
            except Exception as e:
                peer.reputation -= 20
                self.log_event("MALFORMED_MESSAGE_RECEIVED", peer_id=peer.peer_id, object_id=str(e))
                if peer.reputation <= 0:
                    self.banned_peer_ids.add(peer.peer_id)
                    peer.close()
                    break

        peer.close()
        self.peers.pop(peer.peer_id, None)
        self.log_event("PEER_DISCONNECTED", peer_id=peer.peer_id)

    async def _process_message(self, peer: PeerConnection, msg: Dict[str, Any]) -> None:
        m_type = msg.get("type")

        # 1. PING / PONG
        if m_type == "ping":
            await peer.send({"type": "pong", "nonce": msg.get("nonce", 0)})

        # 2. INV (Inventory announcement)
        elif m_type == "inv":
            items = msg.get("inventory", [])
            needed = []
            for item in items:
                i_type = item["type"]
                i_id = item["id"]
                self.log_event("INV_RECEIVED", peer_id=peer.peer_id, object_id=i_id)
                # Check if already have it
                if i_type == "tx" and not self.mempool.contains(i_id):
                    needed.append(item)
                elif i_type == "block" and i_id not in self.chain.block_nodes:
                    needed.append(item)

            if needed:
                await peer.send({"type": "getdata", "inventory": needed})

        # 3. GETDATA (Object request)
        elif m_type == "getdata":
            items = msg.get("inventory", [])
            for item in items:
                i_type = item["type"]
                i_id = item["id"]
                if i_type == "tx" and self.mempool.contains(i_id):
                    tx = self.mempool.txs[i_id]
                    await peer.send({"type": "tx", "tx_data": tx.to_dict()})
                elif i_type == "block" and i_id in self.chain.block_nodes:
                    blk = self.chain.block_nodes[i_id].block
                    await peer.send({"type": "block", "block_data": blk.to_dict()})

        # 4. TX (Transaction arrival)
        elif m_type == "tx":
            try:
                tx = Transaction.from_dict(msg["tx_data"])
                tx_id = tx.tx_id
                self.log_event("TX_RECEIVED", peer_id=peer.peer_id, object_id=tx_id)
                ok, reason = self.mempool.add_transaction(tx, self.chain.utxo_set)
                if ok:
                    self.log_event("TX_ACCEPTED_TO_MEMPOOL", object_id=tx_id)
                    # Relay to other peers
                    await self.broadcast_inventory([{"type": "tx", "id": tx_id}], exclude_peer=peer.peer_id)
            except Exception as e:
                peer.reputation -= 15

        # 5. BLOCK (Block arrival)
        elif m_type == "block":
            try:
                b_dict = msg["block_data"]
                header = BlockHeader(
                    version=b_dict["header"]["version"],
                    prev_block_hash=b_dict["header"]["prev_block_hash"],
                    merkle_root=b_dict["header"]["merkle_root"],
                    timestamp=b_dict["header"]["timestamp"],
                    target=int(b_dict["header"]["target"], 16),
                    nonce=b_dict["header"]["nonce"],
                )
                txs = [Transaction.from_dict(t) for t in b_dict["transactions"]]
                block = Block(header=header, transactions=txs)
                b_hash = block.block_hash

                self.log_event("BLOCK_RECEIVED", peer_id=peer.peer_id, object_id=b_hash)
                ok, reason = self.chain.add_block(block)

                if ok:
                    self.log_event("BLOCK_ACCEPTED", object_id=b_hash)
                    # Clean confirmed transactions from mempool
                    self.mempool.remove_confirmed_transactions(block.transactions)

                    # If reorg occurred, check if any stale transactions can be resurrected to mempool
                    if "REORGANISED" in reason:
                        reorg_record = self.chain.reorg_history[-1]
                        for disc_hash in reorg_record["disconnected_blocks"]:
                            stale_block = self.chain.block_nodes[disc_hash].block
                            self.mempool.resurrect_transactions(stale_block.transactions, self.chain.utxo_set)
                        self.log_event("REORG_COMPLETED", object_id=b_hash)

                    # Gossip to other peers
                    await self.broadcast_inventory([{"type": "block", "id": b_hash}], exclude_peer=peer.peer_id)
                else:
                    self.log_event("BLOCK_REJECTED", object_id=b_hash)
            except Exception as e:
                peer.reputation -= 25

    async def broadcast_inventory(self, items: List[Dict[str, str]], exclude_peer: str = "") -> None:
        """Gossips inventory announcement to all connected peers."""
        msg = {"type": "inv", "inventory": items}
        for peer_id, peer in list(self.peers.items()):
            if peer_id != exclude_peer:
                await peer.send(msg)

    async def broadcast_transaction(self, tx: Transaction) -> bool:
        """Submits a local transaction to mempool and broadcasts inventory."""
        ok, reason = self.mempool.add_transaction(tx, self.chain.utxo_set)
        if ok:
            self.log_event("LOCAL_TX_CREATED", object_id=tx.tx_id)
            await self.broadcast_inventory([{"type": "tx", "id": tx.tx_id}])
            return True
        return False

    async def broadcast_mined_block(self, block: Block) -> bool:
        """Applies locally mined block and broadcasts inventory."""
        ok, reason = self.chain.add_block(block)
        if ok:
            b_hash = block.block_hash
            self.log_event("LOCAL_BLOCK_MINED", object_id=b_hash)
            self.mempool.remove_confirmed_transactions(block.transactions)
            await self.broadcast_inventory([{"type": "block", "id": b_hash}])
            return True
        return False

