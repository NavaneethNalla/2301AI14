"""
p2p.mempool
===========
In-memory transaction pool supporting:
- UTXO validation and double-spend conflict detection
- Duplicate suppression
- Fee-rate ordering (fee / byte_size) for block templates
- TTL expiration
- Transaction resurrection on chain reorganisations
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from chain.models import OutPoint, Transaction, TxOutput
from utxo.models import compute_pubkey_hash

DEFAULT_MEMPOOL_TTL = 300.0  # 5 minutes


class Mempool:
    """
    Transaction mempool with fee-rate prioritization and conflict protection.
    """

    def __init__(self, ttl: float = DEFAULT_MEMPOOL_TTL) -> None:
        self.ttl = ttl
        self.txs: Dict[str, Transaction] = {}
        # Maps OutPoint to tx_id in mempool that spends it (prevents mempool double-spends)
        self.spent_outpoints: Dict[OutPoint, str] = {}
        self.entry_times: Dict[str, float] = {}
        self.fees: Dict[str, int] = {}
        self.sizes: Dict[str, int] = {}

    def contains(self, tx_id: str) -> bool:
        return tx_id in self.txs

    def add_transaction(
        self,
        tx: Transaction,
        ledger_utxos: Dict[OutPoint, TxOutput],
    ) -> Tuple[bool, str]:
        """
        Validates and adds an unconfirmed transaction to the mempool.
        Rejects duplicates, conflicts, and invalid state transitions.
        """
        self.purge_expired()

        tx_id = tx.tx_id
        if tx_id in self.txs:
            return False, "DUPLICATE_IN_MEMPOOL"

        if tx.is_coinbase:
            return False, "REJECT_COINBASE_IN_MEMPOOL"

        if not tx.inputs or not tx.outputs:
            return False, "REJECT_EMPTY_TX"

        # Check for conflicts with existing unconfirmed mempool transactions
        for inp in tx.inputs:
            op = inp.outpoint
            if op in self.spent_outpoints:
                conflicting_tx = self.spent_outpoints[op]
                return False, f"REJECT_MEMPOOL_CONFLICT: OutPoint {op.to_str()} already spent by tx {conflicting_tx}."

        # Validate against ledger UTXOs
        total_in = 0
        for in_idx, inp in enumerate(tx.inputs):
            op = inp.outpoint
            utxo = ledger_utxos.get(op)
            if utxo is None:
                return False, f"REJECT_MISSING_UTXO: OutPoint {op.to_str()} not found in confirmed UTXO set."

            pub_bytes = bytes.fromhex(inp.pubkey_hex)
            if compute_pubkey_hash(pub_bytes) != utxo.pubkey_hash:
                return False, f"REJECT_LOCK_MISMATCH: Input {in_idx} does not satisfy P2PKH lock."

            sighash = tx.compute_sighash(in_idx)
            pub_obj = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            try:
                pub_obj.verify(bytes.fromhex(inp.signature_hex), sighash)
            except InvalidSignature:
                return False, f"REJECT_BAD_SIG: Input {in_idx} signature invalid."

            total_in += utxo.value

        total_out = sum(out.value for out in tx.outputs)
        if total_in < total_out:
            return False, "REJECT_VALUE_CREATION"

        fee = total_in - total_out
        tx_size = len(str(tx.to_dict()).encode("utf-8"))

        # Add to mempool
        self.txs[tx_id] = tx
        self.entry_times[tx_id] = time.time()
        self.fees[tx_id] = fee
        self.sizes[tx_id] = max(tx_size, 1)

        for inp in tx.inputs:
            self.spent_outpoints[inp.outpoint] = tx_id

        return True, "ACCEPTED"

    def remove_transaction(self, tx_id: str) -> None:
        """Removes a transaction and frees its spent outpoints."""
        tx = self.txs.pop(tx_id, None)
        if tx:
            for inp in tx.inputs:
                self.spent_outpoints.pop(inp.outpoint, None)
            self.entry_times.pop(tx_id, None)
            self.fees.pop(tx_id, None)
            self.sizes.pop(tx_id, None)

    def remove_confirmed_transactions(self, confirmed_txs: List[Transaction]) -> None:
        """Removes transactions that have been confirmed in newly connected blocks."""
        for tx in confirmed_txs:
            self.remove_transaction(tx.tx_id)
            # Also clean up any mempool transactions that conflict with newly spent outpoints
            for inp in tx.inputs:
                conflicting_tx_id = self.spent_outpoints.get(inp.outpoint)
                if conflicting_tx_id and conflicting_tx_id != tx.tx_id:
                    self.remove_transaction(conflicting_tx_id)

    def resurrect_transactions(
        self,
        disconnected_txs: List[Transaction],
        current_ledger_utxos: Dict[OutPoint, TxOutput],
    ) -> None:
        """
        When a block is disconnected during a reorganisation, restores valid,
        non-conflicting non-coinbase transactions back to the mempool.
        """
        for tx in disconnected_txs:
            if not tx.is_coinbase:
                self.add_transaction(tx, current_ledger_utxos)

    def get_block_template(self, max_tx_count: int = 500) -> List[Transaction]:
        """
        Selects transactions ordered by fee-rate (fee / size) DESCENDING.
        """
        self.purge_expired()

        def fee_rate(tx_id: str) -> float:
            return self.fees[tx_id] / self.sizes[tx_id]

        sorted_tx_ids = sorted(self.txs.keys(), key=fee_rate, reverse=True)
        return [self.txs[tx_id] for tx_id in sorted_tx_ids[:max_tx_count]]

    def purge_expired(self) -> None:
        """Purges transactions that exceeded the TTL."""
        now = time.time()
        expired = [tx_id for tx_id, t in self.entry_times.items() if now - t > self.ttl]
        for tx_id in expired:
            self.remove_transaction(tx_id)

