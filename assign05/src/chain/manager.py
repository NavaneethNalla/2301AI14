"""
chain.manager
=============
Node-local blockchain manager supporting:
- Full block and state-transition validation
- Cumulative work tracking
- Fork resolution and atomic chain reorganisation
"""

from __future__ import annotations

import copy
import hashlib
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

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

DEFAULT_SUBSIDY = 50
GENESIS_PREV_HASH = "00" * 32
EASY_TARGET = (1 << 248) - 1  # 8 leading zero bits for fast demonstrative mining


def compute_pubkey_hash(pubkey_bytes: bytes) -> str:
    sha = hashlib.sha256(pubkey_bytes).digest()
    return hashlib.new("ripemd160", sha).hexdigest()


class BlockNode:
    """Node in the block tree hierarchy."""

    def __init__(
        self,
        block: Block,
        height: int,
        cumulative_work: int,
        parent_hash: Optional[str] = None,
    ) -> None:
        self.block = block
        self.height = height
        self.cumulative_work = cumulative_work
        self.parent_hash = parent_hash
        self.children_hashes: List[str] = []


class ChainManager:
    """
    Blockchain manager enforcing PoW, UTXO ledger progression,
    cumulative work selection, and atomic reorganisations.
    """

    def __init__(self, genesis_target: int = EASY_TARGET, subsidy: int = DEFAULT_SUBSIDY) -> None:
        self.subsidy = subsidy
        self.block_nodes: Dict[str, BlockNode] = {}
        self.active_tip_hash: str = ""
        self.utxo_set: Dict[OutPoint, TxOutput] = {}
        # Stores the UTXO diffs per block: {block_hash: {"spent": {op: out}, "created": [op]}}
        self.block_diffs: Dict[str, Dict[str, Any]] = {}
        self.reorg_history: List[Dict[str, Any]] = []

        self._create_genesis_block(genesis_target)

    def _create_genesis_block(self, target: int) -> None:
        # Genesis coinbase paying to standard burn/genesis address
        genesis_cb = create_coinbase_tx(recipient_pubkey_hash="00" * 20, subsidy=self.subsidy, total_fees=0, extra_data="GENESIS BLOCK")
        tx_leaf = hashlib.sha256(b"\x00" + bytes.fromhex(genesis_cb.tx_id)).digest()
        merkle = tx_leaf.hex()

        header = BlockHeader(
            version=1,
            prev_block_hash=GENESIS_PREV_HASH,
            merkle_root=merkle,
            timestamp=1700000000,
            target=target,
            nonce=0,
        )
        mined_header, _, _ = mine_block_header(header)
        genesis_block = Block(header=mined_header, transactions=[genesis_cb])

        g_hash = genesis_block.block_hash
        node = BlockNode(block=genesis_block, height=0, cumulative_work=mined_header.work, parent_hash=None)
        self.block_nodes[g_hash] = node
        self.active_tip_hash = g_hash

        # Add genesis coinbase to UTXO set
        g_op = OutPoint(genesis_cb.tx_id, 0)
        self.utxo_set[g_op] = genesis_cb.outputs[0]
        self.block_diffs[g_hash] = {"spent": {}, "created": [g_op]}

    @property
    def active_tip(self) -> BlockNode:
        return self.block_nodes[self.active_tip_hash]

    @property
    def active_height(self) -> int:
        return self.active_tip.height

    @property
    def active_cumulative_work(self) -> int:
        return self.active_tip.cumulative_work

    def validate_block_transactions(
        self,
        block: Block,
        working_utxo_set: Dict[OutPoint, TxOutput],
    ) -> Tuple[bool, str, Dict[OutPoint, TxOutput], List[OutPoint]]:
        """
        Validates transactions sequentially against working UTXO set.
        Returns: (is_valid, error_msg, spent_utxos_dict, created_outpoints_list)
        """
        if not block.transactions:
            return False, "REJECT_NO_TRANSACTIONS: Block must contain transactions.", {}, []

        # 1. Coinbase check
        cb = block.transactions[0]
        if not cb.is_coinbase:
            return False, "REJECT_NO_COINBASE: First transaction must be a coinbase.", {}, []

        # Ensure no other coinbase in block
        for i in range(1, len(block.transactions)):
            if block.transactions[i].is_coinbase:
                return False, f"REJECT_EXTRA_COINBASE: Transaction {i} is an illegal secondary coinbase.", {}, []

        spent_in_block: Dict[OutPoint, TxOutput] = {}
        created_in_block: List[OutPoint] = []
        total_block_fees = 0

        # Process non-coinbase transactions
        for tx_idx in range(1, len(block.transactions)):
            tx = block.transactions[tx_idx]
            if not tx.inputs or not tx.outputs:
                return False, f"REJECT_EMPTY_TX: Transaction {tx_idx} must have inputs and outputs.", {}, []

            seen_ops = set()
            tx_in_val = 0
            for in_idx, inp in enumerate(tx.inputs):
                op = inp.outpoint
                if op in seen_ops:
                    return False, f"REJECT_DUPLICATE_INPUT: OutPoint {op.to_str()} spent multiple times in tx.", {}, []
                seen_ops.add(op)

                utxo = working_utxo_set.get(op)
                if utxo is None:
                    return False, f"REJECT_MISSING_UTXO: OutPoint {op.to_str()} not found or already spent.", {}, []

                # Verify P2PKH pubkey
                pub_bytes = bytes.fromhex(inp.pubkey_hex)
                if compute_pubkey_hash(pub_bytes) != utxo.pubkey_hash:
                    return False, f"REJECT_LOCK_MISMATCH: Input {in_idx} does not satisfy P2PKH lock.", {}, []

                # Verify signature
                sighash = tx.compute_sighash(in_idx)
                pub_obj = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
                try:
                    pub_obj.verify(bytes.fromhex(inp.signature_hex), sighash)
                except InvalidSignature:
                    return False, f"REJECT_BAD_SIG: Input {in_idx} signature verification failed.", {}, []

                tx_in_val += utxo.value

            tx_out_val = 0
            for out_idx, out in enumerate(tx.outputs):
                if out.value <= 0:
                    return False, f"REJECT_INVALID_OUTPUT_VAL: Output {out_idx} value must be positive.", {}, []
                tx_out_val += out.value

            if tx_in_val < tx_out_val:
                return False, f"REJECT_VALUE_CREATION: Tx {tx_idx} creates value out of thin air.", {}, []

            tx_fee = tx_in_val - tx_out_val
            total_block_fees += tx_fee

            # Apply tx to working_utxo_set
            for inp in tx.inputs:
                op = inp.outpoint
                spent_in_block[op] = working_utxo_set.pop(op)

            for out_idx, out in enumerate(tx.outputs):
                new_op = OutPoint(tx.tx_id, out_idx)
                working_utxo_set[new_op] = out
                created_in_block.append(new_op)

        # 2. Verify coinbase subsidy + fees limit
        cb_out_val = sum(out.value for out in cb.outputs)
        max_allowed_cb = self.subsidy + total_block_fees
        if cb_out_val > max_allowed_cb:
            return (
                False,
                f"REJECT_EXCESS_COINBASE: Coinbase reward {cb_out_val} exceeds allowed max {max_allowed_cb}.",
                {},
                [],
            )

        # Apply coinbase to working_utxo_set
        for out_idx, out in enumerate(cb.outputs):
            cb_op = OutPoint(cb.tx_id, out_idx)
            working_utxo_set[cb_op] = out
            created_in_block.append(cb_op)

        return True, "VALID", spent_in_block, created_in_block

    def _find_common_ancestor(self, hash_a: str, hash_b: str) -> str:
        ancestors_a = set()
        curr = hash_a
        while curr:
            ancestors_a.add(curr)
            curr = self.block_nodes[curr].parent_hash or ""

        curr = hash_b
        while curr:
            if curr in ancestors_a:
                return curr
            curr = self.block_nodes[curr].parent_hash or ""

        raise RuntimeError("No common ancestor found (broken genesis tree).")

    def _get_path_from_ancestor(self, start_hash: str, ancestor_hash: str) -> List[str]:
        path = []
        curr = start_hash
        while curr != ancestor_hash:
            path.append(curr)
            curr = self.block_nodes[curr].parent_hash or ""
        path.reverse()
        return path

    def add_block(self, block: Block) -> Tuple[bool, str]:
        """
        Processes a newly mined or received block.
        Performs PoW checks, Merkle root checks, cumulative work comparison,
        and reorganisation if new branch has strictly more work.
        """
        b_hash = block.block_hash
        header = block.header

        if b_hash in self.block_nodes:
            return False, "REJECT_DUPLICATE_BLOCK: Block already exists."

        # 1. PoW check
        if header.hash_int > header.target:
            return False, f"REJECT_INVALID_POW: Header hash {header.hash_hex} does not meet target."

        # 2. Check parent exists
        parent_hash = header.prev_block_hash
        parent_node = self.block_nodes.get(parent_hash)
        if not parent_node:
            return False, f"REJECT_ORPHAN_BLOCK: Previous block {parent_hash} not found."

        # 3. Check Merkle root matches block transactions
        computed_merkle = block.compute_merkle_root()
        if header.merkle_root != computed_merkle:
            return (
                False,
                f"REJECT_MERKLE_ROOT_MISMATCH: Header root {header.merkle_root} != computed {computed_merkle}.",
            )

        # Compute new node stats
        new_height = parent_node.height + 1
        new_cumulative_work = parent_node.cumulative_work + header.work
        node = BlockNode(block=block, height=new_height, cumulative_work=new_cumulative_work, parent_hash=parent_hash)

        # Check if extending active tip directly
        if parent_hash == self.active_tip_hash:
            working_utxo = dict(self.utxo_set)
            valid, reason, spent, created = self.validate_block_transactions(block, working_utxo)
            if not valid:
                return False, reason

            # Update active tip
            self.block_nodes[b_hash] = node
            parent_node.children_hashes.append(b_hash)
            self.active_tip_hash = b_hash
            self.utxo_set = working_utxo
            self.block_diffs[b_hash] = {"spent": spent, "created": created}
            return True, "ACCEPTED_EXTENDED_ACTIVE_TIP"

        # Otherwise, block is on a fork
        self.block_nodes[b_hash] = node
        parent_node.children_hashes.append(b_hash)

        # Check if new branch has strictly more cumulative work than active tip
        if new_cumulative_work > self.active_cumulative_work:
            # TRIGGER CHAIN REORGANISATION
            ancestor_hash = self._find_common_ancestor(self.active_tip_hash, b_hash)
            disconnect_path = self._get_path_from_ancestor(self.active_tip_hash, ancestor_hash)
            connect_path = self._get_path_from_ancestor(b_hash, ancestor_hash)

            # Reconstruct UTXO set at common ancestor
            temp_utxo = dict(self.utxo_set)
            # Roll back active branch blocks in reverse
            for blk_hash in reversed(disconnect_path):
                diff = self.block_diffs[blk_hash]
                # Remove outputs created by this block
                for op in diff["created"]:
                    temp_utxo.pop(op, None)
                # Restore outputs spent by this block
                for op, out in diff["spent"].items():
                    temp_utxo[op] = out

            # Now sequentially connect and validate blocks on the new branch
            new_diffs: Dict[str, Dict[str, Any]] = {}
            for blk_hash in connect_path:
                curr_block = self.block_nodes[blk_hash].block
                valid, reason, spent, created = self.validate_block_transactions(curr_block, temp_utxo)
                if not valid:
                    # REORG ABORTED! Clean rollback to active chain
                    return False, f"REORG_FAILED_INVALID_BRANCH_BLOCK: {reason}"
                new_diffs[blk_hash] = {"spent": spent, "created": created}

            # Reorg successful: Commit new active tip and UTXO set
            self.block_diffs.update(new_diffs)
            self.utxo_set = temp_utxo
            old_tip = self.active_tip_hash
            self.active_tip_hash = b_hash

            self.reorg_history.append({
                "from_tip": old_tip,
                "to_tip": b_hash,
                "common_ancestor": ancestor_hash,
                "disconnected_blocks": disconnect_path,
                "connected_blocks": connect_path,
                "new_cumulative_work": new_cumulative_work,
            })

            return True, f"ACCEPTED_REORGANISED: Switched active tip to higher work branch ({b_hash[:16]}...)"

        return True, "ACCEPTED_FORK_BLOCK_STORED"

