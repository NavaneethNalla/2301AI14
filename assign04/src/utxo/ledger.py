"""
utxo.ledger
===========
In-memory UTXO ledger engine with strict P2PKH validation, atomic updates,
deterministic coin selection, snapshot persistence, and transaction building.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from utxo.models import (
    OutPoint,
    Transaction,
    TxInput,
    TxOutput,
    compute_pubkey_hash,
)

MAX_INT64 = 2**63 - 1


class ValidationError(Exception):
    """Raised when a transaction fails validation rules."""
    pass


class Ledger:
    """
    In-memory UTXO ledger managing confirmed unspent outputs.
    """

    def __init__(self) -> None:
        self.utxos: Dict[OutPoint, TxOutput] = {}
        self.execution_trace: List[Dict[str, Any]] = []

    def add_utxo(self, outpoint: OutPoint, output: TxOutput) -> None:
        """Directly adds a UTXO (e.g. genesis or test harness)."""
        self.utxos[outpoint] = output

    def get_utxo(self, outpoint: OutPoint) -> Optional[TxOutput]:
        return self.utxos.get(outpoint)

    def validate_transaction(self, tx: Transaction) -> Tuple[bool, int, str]:
        """
        Validates transaction against current ledger state.
        Returns: (is_valid, fee, reason_or_success_message)
        """
        # 1. Structure checks
        if not tx.inputs:
            return False, 0, "REJECT_EMPTY_INPUTS: Transaction must have at least one input."
        if not tx.outputs:
            return False, 0, "REJECT_EMPTY_OUTPUTS: Transaction must have at least one output."

        # 2. Duplicate inputs within same transaction
        seen_outpoints = set()
        for i, inp in enumerate(tx.inputs):
            op = inp.outpoint
            if op in seen_outpoints:
                return False, 0, f"REJECT_DUPLICATE_INPUT: OutPoint {op.to_str()} referenced multiple times in same tx."
            seen_outpoints.add(op)

        # 3. Output range and arithmetic overflow checks
        total_output_value = 0
        for i, out in enumerate(tx.outputs):
            if out.value <= 0:
                return False, 0, f"REJECT_INVALID_OUTPUT_VALUE: Output {i} value must be positive, got {out.value}."
            if out.value > MAX_INT64:
                return False, 0, f"REJECT_INTEGER_OVERFLOW: Output {i} value exceeds MAX_INT64."
            total_output_value += out.value
            if total_output_value > MAX_INT64:
                return False, 0, "REJECT_INTEGER_OVERFLOW: Sum of outputs exceeds MAX_INT64."

        # 4. Input validation and P2PKH script verification
        total_input_value = 0
        for i, inp in enumerate(tx.inputs):
            op = inp.outpoint
            utxo = self.utxos.get(op)
            if utxo is None:
                return False, 0, f"REJECT_MISSING_UTXO: Referenced OutPoint {op.to_str()} does not exist in ledger."

            # Check pubkey hex
            clean_pub = inp.pubkey_hex.strip().lower()
            if len(clean_pub) != 64:
                return False, 0, f"REJECT_MALFORMED_PUBKEY: Input {i} public key must be 32 bytes (64 hex chars)."
            try:
                pub_bytes = bytes.fromhex(clean_pub)
            except ValueError:
                return False, 0, f"REJECT_MALFORMED_PUBKEY: Input {i} public key is not valid hex."

            # Verify P2PKH locking condition
            derived_pkh = compute_pubkey_hash(pub_bytes)
            if derived_pkh != utxo.pubkey_hash:
                return (
                    False,
                    0,
                    f"REJECT_LOCK_MISMATCH: Input {i} pubkey hash {derived_pkh} does not match UTXO lock {utxo.pubkey_hash}.",
                )

            # Verify signature
            clean_sig = inp.signature_hex.strip().lower()
            if len(clean_sig) != 128:
                return False, 0, f"REJECT_MALFORMED_SIG: Input {i} signature must be 64 bytes (128 hex chars)."
            try:
                sig_bytes = bytes.fromhex(clean_sig)
            except ValueError:
                return False, 0, f"REJECT_MALFORMED_SIG: Input {i} signature is not valid hex."

            sighash = tx.compute_sighash(i)
            pubkey_obj = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            try:
                pubkey_obj.verify(sig_bytes, sighash)
            except InvalidSignature:
                return False, 0, f"REJECT_BAD_SIGNATURE: Input {i} signature failed cryptographic verification."

            total_input_value += utxo.value
            if total_input_value > MAX_INT64:
                return False, 0, "REJECT_INTEGER_OVERFLOW: Sum of inputs exceeds MAX_INT64."

        # 5. Conservation of value: inputs >= outputs
        if total_input_value < total_output_value:
            return (
                False,
                0,
                f"REJECT_VALUE_CREATION: Total inputs ({total_input_value}) < total outputs ({total_output_value}).",
            )

        fee = total_input_value - total_output_value
        return True, fee, "ACCEPTED"

    def apply_transaction(self, tx: Transaction) -> Tuple[bool, int, str]:
        """
        Validates and applies a transaction ATOMICALLY.
        If validation fails, ledger state remains 100% unchanged.
        """
        is_valid, fee, reason = self.validate_transaction(tx)
        tx_id = tx.tx_id

        trace_entry = {
            "tx_id": tx_id,
            "status": "ACCEPTED" if is_valid else "REJECTED",
            "fee": fee,
            "reason": reason,
        }
        self.execution_trace.append(trace_entry)

        if not is_valid:
            return False, 0, reason

        # ATOMIC STATE MUTATION
        # 1. Consume spent UTXOs
        for inp in tx.inputs:
            del self.utxos[inp.outpoint]

        # 2. Insert newly created UTXOs
        for out_idx, out in enumerate(tx.outputs):
            new_op = OutPoint(tx_id, out_idx)
            self.utxos[new_op] = out

        return True, fee, "ACCEPTED"

    def select_coins_largest_first(
        self,
        owner_pubkey_hash: str,
        target_amount: int,
        fee: int,
    ) -> Tuple[List[Tuple[OutPoint, TxOutput]], int]:
        """
        Deterministic Coin Selection: Largest-First Strategy.
        - Gathers all UTXOs owned by owner_pubkey_hash.
        - Sorts by value DESCENDING, tie-breaking by (tx_id, output_index) ASCENDING.
        - Greedily selects until accumulated >= target_amount + fee.
        - Returns (selected_list, change_amount).
        """
        required_total = target_amount + fee
        clean_pkh = owner_pubkey_hash.strip().lower()

        candidate_utxos = [
            (op, out) for op, out in self.utxos.items() if out.pubkey_hash == clean_pkh
        ]

        # Sort: value DESC, then tx_id ASC, then output_index ASC
        candidate_utxos.sort(key=lambda item: (-item[1].value, item[0].tx_id, item[0].output_index))

        selected: List[Tuple[OutPoint, TxOutput]] = []
        accumulated = 0

        for op, out in candidate_utxos:
            selected.append((op, out))
            accumulated += out.value
            if accumulated >= required_total:
                break

        if accumulated < required_total:
            raise ValueError(
                f"Insufficient funds: required {required_total} (amount {target_amount} + fee {fee}), available {accumulated}."
            )

        change = accumulated - required_total
        return selected, change

    def build_and_sign_transaction(
        self,
        priv_key_bytes: bytes,
        recipient_pubkey_hash: str,
        amount: int,
        fee: int,
    ) -> Transaction:
        """
        Wallet transaction builder:
        - Derives sender pubkey and pubkey_hash from private key.
        - Performs Largest-First coin selection.
        - Builds outputs (recipient output + change output if change > 0).
        - Signs each input with private key.
        - Returns fully formed, valid Transaction.
        """
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(priv_key_bytes)
        pub_bytes = priv.public_key().public_bytes_raw()
        sender_pkh = compute_pubkey_hash(pub_bytes)

        selected_utxos, change_val = self.select_coins_largest_first(sender_pkh, amount, fee)

        # Build outputs
        outputs = [TxOutput(value=amount, pubkey_hash=recipient_pubkey_hash)]
        if change_val > 0:
            outputs.append(TxOutput(value=change_val, pubkey_hash=sender_pkh))

        # Build unsigned inputs
        inputs = [
            TxInput(prev_tx_id=op.tx_id, prev_out_index=op.output_index)
            for op, _ in selected_utxos
        ]

        tx = Transaction(inputs=inputs, outputs=outputs)

        # Sign each input
        for i in range(len(inputs)):
            sighash = tx.compute_sighash(i)
            sig = priv.sign(sighash)
            tx.inputs[i].signature_hex = sig.hex()
            tx.inputs[i].pubkey_hex = pub_bytes.hex()

        return tx

    def save_snapshot(self, filepath: str | Path) -> None:
        """Serializes current UTXO set to a deterministic JSON file."""
        path = Path(filepath)
        snapshot = {
            op.to_str(): out.to_dict()
            for op, out in sorted(self.utxos.items(), key=lambda item: (item[0].tx_id, item[0].output_index))
        }
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    @classmethod
    def load_snapshot(cls, filepath: str | Path) -> Ledger:
        """Loads UTXO set from JSON file without changing logical contents."""
        path = Path(filepath)
        raw = json.loads(path.read_text(encoding="utf-8"))
        ledger = cls()
        for op_str, out_dict in raw.items():
            op = OutPoint.from_str(op_str)
            out = TxOutput.from_dict(out_dict)
            ledger.add_utxo(op, out)
        return ledger

