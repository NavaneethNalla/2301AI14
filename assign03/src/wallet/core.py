"""
wallet.core
===========
Cryptographic wallet core routines for Assignment 3:
- Ed25519 key generation with secure OS entropy
- Base58Check address derivation (version byte 0x6f + RIPEMD160(SHA256(pubkey)) + checksum)
- Deterministic canonical transaction serialization
- Ed25519 signing and independent verification
- Strict rejection rules (replay, tamper, malleability, address mismatch)
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Dict, Optional, Tuple
import unicodedata

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

# Configuration defaults
DEFAULT_VERSION_BYTE = b"\x6f"  # Standard testnet version byte
DEFAULT_NETWORK_ID = "course-testnet"
B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

TEST_KEY_WARNING = (
    "# ====================================================================\n"
    "# WARNING: TEST ONLY - DO NOT USE ON MAINNET\n"
    "# This private key was generated for educational testing purposes.\n"
    "# Never fund this key with real value or deploy to production networks.\n"
    "# ====================================================================\n"
)


# ---------------------------------------------------------------------------
# Base58 and Base58Check Encoding / Decoding
# ---------------------------------------------------------------------------

def b58encode(data: bytes) -> str:
    """Encodes arbitrary byte sequences into Base58."""
    # Count leading zero bytes
    orig_len = len(data)
    stripped = data.lstrip(b"\x00")
    num_zeros = orig_len - len(stripped)

    if not stripped:
        return "1" * num_zeros

    num = int.from_bytes(stripped, "big")
    chars = []
    while num > 0:
        num, rem = divmod(num, 58)
        chars.append(B58_ALPHABET[rem])

    return ("1" * num_zeros) + "".join(reversed(chars))


def b58decode(s: str) -> bytes:
    """Decodes a Base58 string into raw bytes."""
    if not s:
        return b""

    # Count leading '1's
    num_zeros = len(s) - len(s.lstrip("1"))

    num = 0
    for char in s:
        idx = B58_ALPHABET.find(char)
        if idx == -1:
            raise ValueError(f"Invalid Base58 character: '{char}'")
        num = num * 58 + idx

    if num == 0:
        return b"\x00" * num_zeros

    b = num.to_bytes((num.bit_length() + 7) // 8, "big")
    return (b"\x00" * num_zeros) + b


def b58check_encode(version_byte: bytes, payload: bytes) -> str:
    """
    Encodes payload with a 1-byte version prefix and 4-byte double-SHA256 checksum:
    Base58(version || payload || SHA256(SHA256(version || payload))[:4])
    """
    if len(version_byte) != 1:
        raise ValueError("Version byte must be exactly 1 byte.")
    data = version_byte + payload
    checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    return b58encode(data + checksum)


def b58check_decode(address: str, expected_version: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Decodes and validates a Base58Check address.
    Returns: (version_byte, payload_bytes)
    Raises ValueError on invalid characters, invalid length, checksum failure, or wrong version.
    """
    raw = b58decode(address.strip())
    if len(raw) < 5:
        raise ValueError(f"Address is too short: {len(raw)} bytes (minimum 5 bytes required).")

    version_byte = raw[:1]
    payload = raw[1:-4]
    checksum = raw[-4:]

    data = raw[:-4]
    expected_checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]

    if checksum != expected_checksum:
        raise ValueError(
            f"Invalid Base58Check checksum: expected {expected_checksum.hex()}, got {checksum.hex()}."
        )

    if expected_version is not None and version_byte != expected_version:
        raise ValueError(
            f"Version byte mismatch: expected 0x{expected_version.hex()}, got 0x{version_byte.hex()}."
        )

    return version_byte, payload


# ---------------------------------------------------------------------------
# Key Generation and Address Derivation
# ---------------------------------------------------------------------------

def generate_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generates an Ed25519 keypair using OS cryptographic entropy."""
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    return priv, pub


def pubkey_to_address(pubkey_bytes: bytes, version_byte: bytes = DEFAULT_VERSION_BYTE) -> str:
    """
    Derives standard Base58Check address:
    Address = Base58Check(version_byte, RIPEMD160(SHA256(pubkey_bytes)))
    """
    if len(pubkey_bytes) != 32:
        raise ValueError("Ed25519 public key must be exactly 32 bytes.")
    sha = hashlib.sha256(pubkey_bytes).digest()
    rip = hashlib.new("ripemd160", sha).digest()  # 20-byte pubkey hash
    return b58check_encode(version_byte, rip)


def save_private_key_file(filepath: str | Path, priv_bytes: bytes, pub_bytes: bytes, address: str) -> None:
    """
    Saves a private key file with:
    - Conspicuous warning header
    - Restrictive 0600 file permissions
    """
    path = Path(filepath)
    payload = {
        "_warning": "WARNING: TEST ONLY - DO NOT USE ON MAINNET",
        "key_type": "Ed25519",
        "network_id": DEFAULT_NETWORK_ID,
        "address": address,
        "public_key_hex": pub_bytes.hex(),
        "private_key_hex": priv_bytes.hex(),
    }
    content = TEST_KEY_WARNING + json.dumps(payload, indent=2) + "\n"
    path.write_text(content, encoding="utf-8")

    # Apply restrictive permissions (0600: read/write by owner only)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Canonical Serialization
# ---------------------------------------------------------------------------

def canonicalize_json_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {
            unicodedata.normalize("NFC", str(k)): canonicalize_json_obj(v)
            for k, v in sorted(obj.items(), key=lambda i: unicodedata.normalize("NFC", str(i[0])))
        }
    if isinstance(obj, list):
        return [canonicalize_json_obj(x) for x in obj]
    return obj


def canonical_transaction_bytes(tx: Dict[str, Any]) -> bytes:
    """
    Serializes transaction to deterministic UTF-8 bytes:
    - Lexicographically sorted keys
    - No extraneous whitespace: separators=(',', ':')
    - Unicode NFC normalization
    """
    normalized = canonicalize_json_obj(tx)
    serialized = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return serialized.encode("utf-8")


# ---------------------------------------------------------------------------
# Signing & Verification
# ---------------------------------------------------------------------------

def sign_transaction(private_key_bytes: bytes, tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Signs a canonical transaction using an Ed25519 private key.
    Returns:
    {
      "transaction": tx,
      "public_key": <64 hex chars>,
      "signature": <128 hex chars>
    }
    """
    if len(private_key_bytes) != 32:
        raise ValueError("Ed25519 private key must be exactly 32 bytes.")

    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    pub_bytes = priv_key.public_key().public_bytes_raw()

    # Validate that sender address matches public key
    sender_addr = tx.get("sender")
    expected_sender = pubkey_to_address(pub_bytes)
    if sender_addr != expected_sender:
        raise ValueError(
            f"Signer mismatch: private key derives address {expected_sender}, but tx sender is {sender_addr}."
        )

    tx_bytes = canonical_transaction_bytes(tx)
    sig_bytes = priv_key.sign(tx_bytes)

    return {
        "transaction": tx,
        "public_key": pub_bytes.hex(),
        "signature": sig_bytes.hex(),
    }


def verify_transaction(
    signed_tx: Dict[str, Any],
    expected_network: str = DEFAULT_NETWORK_ID,
    nonce_tracker: Optional[Dict[str, int]] = None,
) -> bool:
    """
    Independently verifies a signed transaction:
    1. Validates presence and types of all required fields.
    2. Validates network ID matches expected_network.
    3. Validates positive integer amount.
    4. Validates sender and recipient Base58Check addresses and checksums.
    5. Validates public key derives sender address.
    6. Validates signature length and canonical encoding.
    7. Validates Ed25519 signature over canonical transaction bytes.
    8. Nonce replay prevention: ensures tx.nonce > recorded last_nonce for sender.
    """
    if not isinstance(signed_tx, dict):
        raise ValueError("Signed transaction must be a JSON object.")

    for field in ("transaction", "public_key", "signature"):
        if field not in signed_tx:
            raise ValueError(f"Signed transaction missing top-level field: '{field}'")

    tx = signed_tx["transaction"]
    pub_hex = signed_tx["public_key"]
    sig_hex = signed_tx["signature"]

    required_tx_fields = {
        "version": int,
        "network_id": str,
        "sender": str,
        "recipient": str,
        "amount_units": int,
        "nonce": int,
        "memo_hash": str,
    }

    for f_name, f_type in required_tx_fields.items():
        if f_name not in tx:
            raise ValueError(f"Transaction missing required field: '{f_name}'")
        if not isinstance(tx[f_name], f_type):
            raise ValueError(f"Field '{f_name}' must be of type {f_type.__name__}.")

    # 1. Network check
    if tx["network_id"] != expected_network:
        raise ValueError(
            f"Network ID mismatch: expected '{expected_network}', got '{tx['network_id']}'."
        )

    # 2. Amount check
    if tx["amount_units"] <= 0:
        raise ValueError(f"Invalid amount_units: {tx['amount_units']}. Must be positive.")

    # 3. Address checks
    b58check_decode(tx["sender"], expected_version=DEFAULT_VERSION_BYTE)
    b58check_decode(tx["recipient"], expected_version=DEFAULT_VERSION_BYTE)

    # 4. Public key checks
    clean_pub_hex = pub_hex.strip().lower()
    if len(clean_pub_hex) != 64:
        raise ValueError(f"Public key hex must be 64 characters (32 bytes), got {len(clean_pub_hex)}.")
    pub_bytes = bytes.fromhex(clean_pub_hex)

    derived_sender = pubkey_to_address(pub_bytes)
    if derived_sender != tx["sender"]:
        raise ValueError(
            f"Public key does not match sender address: derives {derived_sender}, expected {tx['sender']}."
        )

    # 5. Signature checks
    clean_sig_hex = sig_hex.strip().lower()
    if len(clean_sig_hex) != 128:
        raise ValueError(f"Signature hex must be 128 characters (64 bytes), got {len(clean_sig_hex)}.")
    sig_bytes = bytes.fromhex(clean_sig_hex)

    # 6. Verify Ed25519 signature
    pub_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
    tx_canonical_bytes = canonical_transaction_bytes(tx)

    try:
        pub_key_obj.verify(sig_bytes, tx_canonical_bytes)
    except InvalidSignature as e:
        raise ValueError(f"Signature verification failed: invalid signature for transaction content.") from e

    # 7. Nonce replay tracking
    if nonce_tracker is not None:
        sender = tx["sender"]
        last_nonce = nonce_tracker.get(sender, -1)
        if tx["nonce"] <= last_nonce:
            raise ValueError(
                f"Replay attack detected: nonce {tx['nonce']} is not greater than last recorded nonce {last_nonce} for sender {sender}."
            )
        nonce_tracker[sender] = tx["nonce"]

    return True

