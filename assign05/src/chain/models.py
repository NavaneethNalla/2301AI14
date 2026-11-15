"""
chain.models
============
Core data structures for Assignment 5:
- BlockHeader (binary canonical serialization, double-SHA256 hash, work calculation)
- Block (header + transactions, Merkle root commitment)
- Coinbase transaction builder
- Merkle root calculation with domain separation
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import struct
import time
from typing import Any, Dict, List, Optional
import unicodedata

# ---------------------------------------------------------------------------
# Merkle Root Calculation for Blocks (from Assignment 2)
# ---------------------------------------------------------------------------

def hash_leaf(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def hash_node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def compute_merkle_root_of_hashes(hashes: List[bytes]) -> str:
    """Computes Merkle root hex using Assignment 2's domain-separated promotion rule."""
    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    if len(hashes) == 1:
        return hashes[0].hex()

    current_level = list(hashes)
    while len(current_level) > 1:
        next_level = []
        n = len(current_level)
        for i in range(0, n, 2):
            if i + 1 < n:
                next_level.append(hash_node(current_level[i], current_level[i + 1]))
            else:
                next_level.append(current_level[i])
        current_level = next_level

    return current_level[0].hex()


# ---------------------------------------------------------------------------
# Transaction & UTXO Models
# ---------------------------------------------------------------------------

def canonical_json_bytes(obj: Any) -> bytes:
    if isinstance(obj, str):
        normalized = unicodedata.normalize("NFC", obj)
    elif isinstance(obj, dict):
        normalized = {
            unicodedata.normalize("NFC", str(k)): canonical_json_bytes(v).decode("utf-8")
            if not isinstance(v, (int, float, bool, type(None)))
            else v
            for k, v in sorted(obj.items(), key=lambda i: unicodedata.normalize("NFC", str(i[0])))
        }
    elif isinstance(obj, (list, tuple)):
        normalized = [
            json.loads(canonical_json_bytes(x).decode("utf-8"))
            if not isinstance(x, (int, float, bool, type(None)))
            else x
            for x in obj
        ]
    else:
        normalized = obj

    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, order=True)
class OutPoint:
    tx_id: str
    output_index: int

    def to_str(self) -> str:
        return f"{self.tx_id}:{self.output_index}"


@dataclass(frozen=True)
class TxOutput:
    value: int
    pubkey_hash: str  # 40 hex chars

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "pubkey_hash": self.pubkey_hash}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TxOutput:
        return cls(value=int(d["value"]), pubkey_hash=str(d["pubkey_hash"]))


@dataclass
class TxInput:
    prev_tx_id: str
    prev_out_index: int
    signature_hex: str = ""
    pubkey_hex: str = ""

    @property
    def outpoint(self) -> OutPoint:
        return OutPoint(self.prev_tx_id, self.prev_out_index)

    @property
    def is_coinbase(self) -> bool:
        return self.prev_tx_id == ("00" * 32) and self.prev_out_index == 0xFFFFFFFF

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prev_tx_id": self.prev_tx_id,
            "prev_out_index": self.prev_out_index,
            "signature_hex": self.signature_hex,
            "pubkey_hex": self.pubkey_hex,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TxInput:
        return cls(
            prev_tx_id=str(d["prev_tx_id"]),
            prev_out_index=int(d["prev_out_index"]),
            signature_hex=str(d.get("signature_hex", "")),
            pubkey_hex=str(d.get("pubkey_hex", "")),
        )


@dataclass
class Transaction:
    inputs: List[TxInput]
    outputs: List[TxOutput]
    locktime: int = 0

    @property
    def is_coinbase(self) -> bool:
        return len(self.inputs) == 1 and self.inputs[0].is_coinbase

    def compute_sighash(self, input_index: int) -> bytes:
        if input_index < 0 or input_index >= len(self.inputs):
            raise IndexError("Input index out of bounds for sighash.")
        unsigned_inputs = [
            {"prev_tx_id": inp.prev_tx_id, "prev_out_index": inp.prev_out_index}
            for inp in self.inputs
        ]
        skeleton = {
            "inputs": unsigned_inputs,
            "outputs": [out.to_dict() for out in self.outputs],
            "locktime": self.locktime,
            "signed_input_index": input_index,
        }
        return hashlib.sha256(canonical_json_bytes(skeleton)).digest()

    @property
    def tx_id(self) -> str:
        return hashlib.sha256(hashlib.sha256(canonical_json_bytes(self.to_dict())).digest()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "locktime": self.locktime,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Transaction:
        inputs = [TxInput.from_dict(inp) for inp in d["inputs"]]
        outputs = [TxOutput.from_dict(out) for out in d["outputs"]]
        locktime = int(d.get("locktime", 0))
        return cls(inputs=inputs, outputs=outputs, locktime=locktime)


def create_coinbase_tx(recipient_pubkey_hash: str, subsidy: int, total_fees: int, extra_data: str = "") -> Transaction:
    """Creates a valid coinbase transaction satisfying all protocol rules."""
    coinbase_input = TxInput(
        prev_tx_id="00" * 32,
        prev_out_index=0xFFFFFFFF,
        signature_hex=extra_data.encode("utf-8").hex() if extra_data else "00" * 64,
        pubkey_hex="00" * 32,
    )
    coinbase_output = TxOutput(value=subsidy + total_fees, pubkey_hash=recipient_pubkey_hash)
    return Transaction(inputs=[coinbase_input], outputs=[coinbase_output])


# ---------------------------------------------------------------------------
# Block Header & Block Models
# ---------------------------------------------------------------------------

@dataclass
class BlockHeader:
    version: int
    prev_block_hash: str  # 64 hex chars
    merkle_root: str      # 64 hex chars
    timestamp: int        # Unix epoch
    target: int           # 256-bit unsigned integer difficulty target
    nonce: int            # Mining counter

    def serialize(self) -> bytes:
        """
        Binary deterministic canonical encoding:
        - version: 4-byte uint32 big-endian
        - prev_block_hash: 32 raw bytes
        - merkle_root: 32 raw bytes
        - timestamp: 8-byte uint64 big-endian
        - target: 32-byte uint256 big-endian
        - nonce: 8-byte uint64 big-endian
        Total header size: 116 bytes.
        """
        return (
            struct.pack(">I", self.version)
            + bytes.fromhex(self.prev_block_hash)
            + bytes.fromhex(self.merkle_root)
            + struct.pack(">Q", self.timestamp)
            + self.target.to_bytes(32, "big")
            + struct.pack(">Q", self.nonce)
        )

    @classmethod
    def deserialize(cls, b: bytes) -> BlockHeader:
        if len(b) != 116:
            raise ValueError(f"BlockHeader raw bytes must be exactly 116 bytes, got {len(b)}.")
        version = struct.unpack(">I", b[:4])[0]
        prev_hash = b[4:36].hex()
        merkle = b[36:68].hex()
        ts = struct.unpack(">Q", b[68:76])[0]
        target = int.from_bytes(b[76:108], "big")
        nonce = struct.unpack(">Q", b[108:116])[0]
        return cls(version, prev_hash, merkle, ts, target, nonce)

    @property
    def hash_bytes(self) -> bytes:
        raw = self.serialize()
        return hashlib.sha256(hashlib.sha256(raw).digest()).digest()

    @property
    def hash_hex(self) -> str:
        return self.hash_bytes.hex()

    @property
    def hash_int(self) -> int:
        return int.from_bytes(self.hash_bytes, "big")

    @property
    def work(self) -> int:
        """Proof-of-work equivalent: work = 2**256 // (target + 1)"""
        return (2**256) // (self.target + 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "prev_block_hash": self.prev_block_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "target": hex(self.target),
            "nonce": self.nonce,
            "block_hash": self.hash_hex,
        }


@dataclass
class Block:
    header: BlockHeader
    transactions: List[Transaction]

    @property
    def block_hash(self) -> str:
        return self.header.hash_hex

    def compute_merkle_root(self) -> str:
        tx_leaf_hashes = [hash_leaf(bytes.fromhex(tx.tx_id)) for tx in self.transactions]
        return compute_merkle_root_of_hashes(tx_leaf_hashes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
        }
