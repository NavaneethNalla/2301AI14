"""
Unit and integration tests for hashlab (Assignment 1).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tracemalloc
import unicodedata
import pytest

from hashlab.core import (
    CHUNK_SIZE,
    canonicalize_obj,
    flip_bit,
    flip_bit_in_file_stream,
    hamming_distance,
    hash_bytes,
    hash_file,
    parse_canonical_json,
    parse_hex,
    to_canonical_json_bytes,
)


# ---------------------------------------------------------------------------
# Test Vectors & Standard Digest Checks
# ---------------------------------------------------------------------------

def test_nist_empty_string():
    length, h_hex, h_b64 = hash_bytes(b"")
    assert length == 0
    assert h_hex == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert h_b64 == base64.b64encode(bytes.fromhex(h_hex)).decode("ascii")


def test_nist_abc():
    length, h_hex, h_b64 = hash_bytes(b"abc")
    assert length == 3
    assert h_hex == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert h_b64 == base64.b64encode(bytes.fromhex(h_hex)).decode("ascii")


def test_prompt_example_alice_pays_bob():
    raw_no_nl = "Alice pays Bob 10".encode("utf-8")
    length_no_nl, h_hex_no_nl, _ = hash_bytes(raw_no_nl)
    assert length_no_nl == 17
    assert h_hex_no_nl == hashlib.sha256(raw_no_nl).hexdigest()

    raw_with_nl = "Alice pays Bob 10\n".encode("utf-8")
    length_with_nl, h_hex_with_nl, _ = hash_bytes(raw_with_nl)
    assert length_with_nl == 18
    assert h_hex_with_nl == hashlib.sha256(raw_with_nl).hexdigest()


# ---------------------------------------------------------------------------
# Hex Parsing & Validation
# ---------------------------------------------------------------------------

def test_parse_hex_valid():
    assert parse_hex("00ff") == b"\x00\xff"
    assert parse_hex("0x00FF") == b"\x00\xff"
    assert parse_hex("deadbeef") == b"\xde\xad\xbe\xef"


def test_parse_hex_odd_length():
    with pytest.raises(ValueError, match="odd length"):
        parse_hex("123")


def test_parse_hex_invalid_chars():
    with pytest.raises(ValueError, match="Malformed hexadecimal string"):
        parse_hex("12zz")


# ---------------------------------------------------------------------------
# Trailing Newline Sensitivity
# ---------------------------------------------------------------------------

def test_trailing_newline_differences():
    no_nl = b"hello"
    lf = b"hello\n"
    crlf = b"hello\r\n"

    _, h1, _ = hash_bytes(no_nl)
    _, h2, _ = hash_bytes(lf)
    _, h3, _ = hash_bytes(crlf)

    assert h1 != h2
    assert h2 != h3
    assert h1 != h3


# ---------------------------------------------------------------------------
# Canonical JSON Tests
# ---------------------------------------------------------------------------

def test_canonical_json_key_order_and_whitespace():
    j1 = '{"b": 1, "a": 2}'
    j2 = '{\n  "a": 2,\n  "b": 1\n}'
    c1 = parse_canonical_json(j1)
    c2 = parse_canonical_json(j2)
    assert c1 == c2
    assert c1 == b'{"a":2,"b":1}'


def test_canonical_json_unicode_normalization():
    # NFC ('é' as 1 codepoint U+00E9) vs NFD ('e' + U+0301)
    nfc = '{"city": "Montr\u00e9al"}'
    nfd = '{"city": "Montre\u0301al"}'
    c_nfc = parse_canonical_json(nfc)
    c_nfd = parse_canonical_json(nfd)
    assert c_nfc == c_nfd
    assert hash_bytes(c_nfc)[1] == hash_bytes(c_nfd)[1]


def test_canonical_json_int_vs_string():
    j_int = '{"val": 10}'
    j_str = '{"val": "10"}'
    c_int = parse_canonical_json(j_int)
    c_str = parse_canonical_json(j_str)
    assert c_int != c_str
    assert hash_bytes(c_int)[1] != hash_bytes(c_str)[1]


def test_canonical_json_from_file(tmp_path):
    p = tmp_path / "sample.json"
    p.write_text('{"z": 100, "a": 200}', encoding="utf-8")
    canon = parse_canonical_json(str(p))
    assert canon == b'{"a":200,"z":100}'


# ---------------------------------------------------------------------------
# Avalanche Effect & Hamming Distance
# ---------------------------------------------------------------------------

def test_flip_bit_basic():
    data = b"\x00\x00"
    # Flip bit 0 (MSB of byte 0) -> 0x80
    assert flip_bit(data, 0) == b"\x80\x00"
    # Flip bit 7 (LSB of byte 0) -> 0x01
    assert flip_bit(data, 7) == b"\x01\x00"
    # Flip bit 8 (MSB of byte 1) -> 0x00 0x80
    assert flip_bit(data, 8) == b"\x00\x80"


def test_flip_bit_out_of_bounds():
    data = b"abc"  # 24 bits
    with pytest.raises(IndexError):
        flip_bit(data, -1)
    with pytest.raises(IndexError):
        flip_bit(data, 24)


def test_avalanche_hamming_bounds():
    data = "Alice pays Bob 10".encode("utf-8")
    orig_digest = hashlib.sha256(data).digest()

    for bit_idx in [0, 7, 15, 31, 63, 100]:
        mutated = flip_bit(data, bit_idx)
        mutated_digest = hashlib.sha256(mutated).digest()
        dist = hamming_distance(orig_digest, mutated_digest)
        # Expected value is ~128 (50% of 256 bits). It should comfortably be within 85-170
        assert 80 <= dist <= 175, f"Bit flip at {bit_idx} produced abnormal Hamming distance: {dist}"


# ---------------------------------------------------------------------------
# Streaming 100 MB File (O(1) Memory Verification)
# ---------------------------------------------------------------------------

def test_stream_100mb_file_memory_footprint(tmp_path):
    file_path = tmp_path / "test_100mb.bin"
    chunk = b"\x5a" * CHUNK_SIZE
    total_chunks = 1600  # 1600 * 64 KB = 104,857,600 bytes (~100 MB)

    with open(file_path, "wb") as f:
        for _ in range(total_chunks):
            f.write(chunk)

    tracemalloc.start()
    before_alloc, _ = tracemalloc.get_traced_memory()

    total_bytes, sha256_hex, sha256_b64 = hash_file(file_path)

    current_alloc, peak_alloc = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert total_bytes == 100 * 1024 * 1024 + 4857600 or total_bytes == total_chunks * CHUNK_SIZE
    assert len(sha256_hex) == 64
    assert len(sha256_b64) == 44

    # Peak memory allocated during the hash_file execution must be far below 10 MB (typically < 200 KB)
    memory_growth = peak_alloc - before_alloc
    assert memory_growth < 5 * 1024 * 1024, f"Memory growth exceeded limit: {memory_growth} bytes"


def test_stream_file_avalanche(tmp_path):
    file_path = tmp_path / "test_small.bin"
    content = b"Streamed Avalanche Test Input Buffer"
    file_path.write_bytes(content)

    _, orig_hex, _ = hash_file(file_path)
    orig_digest = bytes.fromhex(orig_hex)

    _, mutated_digest = flip_bit_in_file_stream(file_path, 3)
    dist = hamming_distance(orig_digest, mutated_digest)
    assert 80 <= dist <= 175


# ---------------------------------------------------------------------------
# CLI End-to-End Tests
# ---------------------------------------------------------------------------

def test_cli_text_mode():
    cmd = [sys.executable, "-m", "hashlab", "text", "Alice pays Bob 10"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "bytes: 17"
    assert lines[1].startswith("sha256: ")
    assert lines[2].startswith("base64: ")


def test_cli_avalanche_mode():
    cmd = [sys.executable, "-m", "hashlab", "avalanche", "--text", "Alice pays Bob 10", "--bit", "7"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res.returncode == 0
    assert "changed_bits_in_digest: " in res.stdout
    val = int(res.stdout.strip().split(": ")[1])
    assert 0 <= val <= 256


def test_cli_hex_invalid():
    cmd = [sys.executable, "-m", "hashlab", "hex", "123"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res.returncode != 0
    assert "odd length" in res.stderr
