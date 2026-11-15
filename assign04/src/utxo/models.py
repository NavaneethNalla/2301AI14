"""
utxo.models
===========
Data models for UTXO-based ledger:
- OutPoint (tx_id + output_index)
- TxOutput (value + P2PKH pubkey_hash)
- TxInput (prev outpoint reference + signature + pubkey)
- Transaction (deterministic tx_id, sighash computation, canonical serialization)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Tuple
import unicodedata

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519


def canonical_json_bytes(obj: Any) -> bytes:
    """Deterministic UTF-8 serialization with sorted keys and no whitespace."""
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


def compute_pubkey_hash(pubkey_bytes: bytes) -> str:
    """Computes 20-byte P2PKH hash: RIPEMD160(SHA256(pubkey_bytes)).hex()"""
    sha = hashlib.sha256(pubkey_bytes).digest()
    return hashlib.new("ripemd160", sha).hexdigest()


@dataclass(frozen=True, order=True)
class OutPoint:
    tx_id: str
    output_index: int

    def __post_init__(self):
        clean_id = self.tx_id.strip().lower()
        if len(clean_id) != 64:
            raise ValueError(f"OutPoint tx_id must be 64 hex characters, got {len(clean_id)}.")
        if self.output_index < 0:
            raise ValueError(f"OutPoint output_index cannot be negative: {self.output_index}.")
        object.__setattr__(self, "tx_id", clean_id)

    def to_str(self) -> str:
        return f"{self.tx_id}:{self.output_index}"

    @classmethod
    def from_str(cls, s: str) -> OutPoint:
        parts = s.split(":")
        if len(parts) != 2:
            raise ValueError(f"Malformed OutPoint string: {s}")
        return cls(tx_id=parts[0], output_index=int(parts[1]))

    def to_dict(self) -> Dict[str, Any]:
        return {"tx_id": self.tx_id, "output_index": self.output_index}


@dataclass(frozen=True)
class TxOutput:
    value: int
    pubkey_hash: str  # 20-byte hex (40 hex chars)

    def __post_init__(self):
        if not isinstance(self.value, int):
            raise ValueError("Output value must be an integer.")
        if self.value <= 0:
            raise ValueError(f"Output value must be positive, got {self.value}.")
        clean_pkh = self.pubkey_hash.strip().lower()
        if len(clean_pkh) != 40:
            raise ValueError(f"pubkey_hash must be 40 hex characters (20 bytes), got {len(clean_pkh)}.")
        object.__setattr__(self, "pubkey_hash", clean_pkh)

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

    def compute_sighash(self, input_index: int) -> bytes:
        """
        Computes sighash for input at input_index.
        Binds the entire unsigned transaction structure and the specific input index.
        """
        if input_index < 0 or input_index >= len(self.inputs):
            raise IndexError("Input index out of bounds for sighash.")

        unsigned_inputs = [
            {"prev_tx_id": inp.prev_tx_id, "prev_out_index": inp.prev_out_index}
            for inp in self.inputs
        ]
        serialized_outputs = [out.to_dict() for out in self.outputs]

        skeleton = {
            "inputs": unsigned_inputs,
            "outputs": serialized_outputs,
            "locktime": self.locktime,
            "signed_input_index": input_index,
        }
        canonical_bytes = canonical_json_bytes(skeleton)
        return hashlib.sha256(canonical_bytes).digest()

    @property
    def tx_id(self) -> str:
        """
        Deterministic transaction identifier:
        double-SHA256 of canonical serialized transaction bytes.
        """
        canonical_bytes = canonical_json_bytes(self.to_dict())
        return hashlib.sha256(hashlib.sha256(canonical_bytes).digest()).hexdigest()

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

