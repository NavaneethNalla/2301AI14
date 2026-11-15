"""
hashlab.core
============
Core cryptographic and byte-manipulation routines for Assignment 1.
Handles bytes, encodings, SHA-256 diagnostics, streaming, bit manipulation,
and canonical JSON serialization without external cryptographic packages.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Tuple
import unicodedata

CHUNK_SIZE = 65536  # 64 KB streaming buffer


def hash_bytes(data: bytes) -> Tuple[int, str, str]:
    """
    Computes SHA-256 diagnostics for an in-memory byte buffer.

    Returns:
        (byte_length, sha256_hex, sha256_base64)
    """
    digest = hashlib.sha256(data).digest()
    return len(data), digest.hex(), base64.b64encode(digest).decode("ascii")


def hash_file(filepath: str | Path) -> Tuple[int, str, str]:
    """
    Computes SHA-256 diagnostics by streaming a file in fixed-size 64 KB chunks.
    Ensures O(1) memory usage regardless of file size.

    Returns:
        (byte_length, sha256_hex, sha256_base64)
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")

    hasher = hashlib.sha256()
    total_bytes = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            hasher.update(chunk)

    digest = hasher.digest()
    return total_bytes, digest.hex(), base64.b64encode(digest).decode("ascii")


def parse_hex(hex_string: str) -> bytes:
    """
    Strictly validates and decodes a hexadecimal string into bytes.
    Rejects odd-length strings or invalid characters.
    """
    cleaned = hex_string.strip()
    if cleaned.startswith("0x") or cleaned.startswith("0X"):
        cleaned = cleaned[2:]
    if len(cleaned) % 2 != 0:
        raise ValueError(
            f"Malformed hexadecimal string: odd length ({len(cleaned)} digits). Hex strings must have an even number of characters."
        )
    try:
        return bytes.fromhex(cleaned)
    except ValueError as e:
        raise ValueError(f"Malformed hexadecimal string: {e}") from e


def flip_bit(data: bytes, bit_index: int) -> bytes:
    """
    Flips a single bit in the byte string at bit_index (0-indexed, MSB first).
    Bit 0 corresponds to the most significant bit of byte 0.
    """
    total_bits = len(data) * 8
    if bit_index < 0 or bit_index >= total_bits:
        raise IndexError(
            f"Bit index {bit_index} out of range for input of {len(data)} bytes ({total_bits} bits)."
        )

    byte_idx = bit_index // 8
    bit_offset = 7 - (bit_index % 8)  # MSB first
    mutated = bytearray(data)
    mutated[byte_idx] ^= (1 << bit_offset)
    return bytes(mutated)


def flip_bit_in_file_stream(filepath: str | Path, bit_index: int) -> Tuple[int, bytes]:
    """
    Computes the SHA-256 digest of a file with a single bit flipped,
    streaming in 64 KB chunks to preserve O(1) memory.
    """
    path = Path(filepath)
    file_size = os.path.getsize(path)
    total_bits = file_size * 8
    if bit_index < 0 or bit_index >= total_bits:
        raise IndexError(
            f"Bit index {bit_index} out of range for file of {file_size} bytes ({total_bits} bits)."
        )

    target_byte_idx = bit_index // 8
    bit_offset = 7 - (bit_index % 8)

    hasher = hashlib.sha256()
    current_byte_pos = 0

    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            chunk_len = len(chunk)
            chunk_start = current_byte_pos
            chunk_end = current_byte_pos + chunk_len

            if chunk_start <= target_byte_idx < chunk_end:
                # Mutate bit in this chunk
                offset_in_chunk = target_byte_idx - chunk_start
                mutated_chunk = bytearray(chunk)
                mutated_chunk[offset_in_chunk] ^= (1 << bit_offset)
                hasher.update(mutated_chunk)
            else:
                hasher.update(chunk)

            current_byte_pos = chunk_end

    return file_size, hasher.digest()


# Alias for backwards compatibility
hash_file_with_bit_flip = flip_bit_in_file_stream


def hamming_distance(digest_a: bytes, digest_b: bytes) -> int:
    """
    Computes the Hamming distance (number of differing bits) between two 32-byte digests.
    """
    if len(digest_a) != 32 or len(digest_b) != 32:
        raise ValueError("Hamming distance expects two 32-byte (256-bit) digests.")
    return sum(bin(b1 ^ b2).count("1") for b1, b2 in zip(digest_a, digest_b))


def canonicalize_obj(obj: Any) -> Any:
    """
    Recursively canonicalizes JSON data structures:
    - Normalizes all string keys and values to Unicode NFC.
    - Preserves data types (numbers, booleans, null, arrays, objects).
    """
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {
            unicodedata.normalize("NFC", str(k)): canonicalize_obj(v)
            for k, v in sorted(obj.items(), key=lambda item: unicodedata.normalize("NFC", str(item[0])))
        }
    if isinstance(obj, list):
        return [canonicalize_obj(x) for x in obj]
    return obj


def to_canonical_json_bytes(obj: Any) -> bytes:
    """
    Serializes a Python JSON-compatible object to canonical UTF-8 bytes:
    - Sorted dictionary keys
    - Compact separators (no whitespace around commas or colons)
    - Unicode NFC normalization
    - UTF-8 encoding without BOM
    """
    normalized = canonicalize_obj(obj)
    serialized = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return serialized.encode("utf-8")


def parse_canonical_json(raw_input: str) -> bytes:
    """
    Parses a JSON string or file path, canonicalizes it, and returns canonical UTF-8 bytes.
    """
    path = Path(raw_input)
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    else:
        obj = json.loads(raw_input)
    return to_canonical_json_bytes(obj)
