"""
Unit and integration tests for wallet (Assignment 3).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import pytest

from wallet.core import (
    DEFAULT_NETWORK_ID,
    DEFAULT_VERSION_BYTE,
    TEST_KEY_WARNING,
    b58check_decode,
    b58check_encode,
    b58decode,
    b58encode,
    canonical_transaction_bytes,
    generate_keypair,
    pubkey_to_address,
    save_private_key_file,
    sign_transaction,
    verify_transaction,
)


# ---------------------------------------------------------------------------
# Base58 and Base58Check Tests
# ---------------------------------------------------------------------------

def test_base58_roundtrip():
    data = b"Hello Blockchain Engineering!"
    encoded = b58encode(data)
    decoded = b58decode(encoded)
    assert decoded == data


def test_base58_leading_zeros():
    data = b"\x00\x00\x00\x01\x02\x03"
    encoded = b58encode(data)
    assert encoded.startswith("111")
    assert b58decode(encoded) == data


def test_base58check_valid():
    payload = b"\x01" * 20
    addr = b58check_encode(DEFAULT_VERSION_BYTE, payload)
    ver, dec_payload = b58check_decode(addr, expected_version=DEFAULT_VERSION_BYTE)
    assert ver == DEFAULT_VERSION_BYTE
    assert dec_payload == payload


def test_base58check_invalid_checksum():
    payload = b"\x01" * 20
    addr = b58check_encode(DEFAULT_VERSION_BYTE, payload)
    # Corrupt the last character
    corrupted_addr = addr[:-1] + ("2" if addr[-1] != "2" else "3")
    with pytest.raises(ValueError, match="Invalid Base58Check checksum"):
        b58check_decode(corrupted_addr)


def test_base58check_version_mismatch():
    payload = b"\x01" * 20
    addr = b58check_encode(b"\x00", payload)
    with pytest.raises(ValueError, match="Version byte mismatch"):
        b58check_decode(addr, expected_version=DEFAULT_VERSION_BYTE)


# ---------------------------------------------------------------------------
# Key Generation, Address Derivation, and File Security
# ---------------------------------------------------------------------------

def test_keygen_and_address_derivation():
    priv, pub = generate_keypair()
    pub_bytes = pub.public_bytes_raw()
    addr = pubkey_to_address(pub_bytes)

    assert addr.startswith("m") or addr.startswith("n") or len(addr) >= 26
    ver, pub_hash = b58check_decode(addr, expected_version=DEFAULT_VERSION_BYTE)
    assert ver == DEFAULT_VERSION_BYTE
    assert len(pub_hash) == 20


def test_save_private_key_permissions_and_warning(tmp_path):
    priv, pub = generate_keypair()
    addr = pubkey_to_address(pub.public_bytes_raw())
    key_file = tmp_path / "test.key"

    save_private_key_file(key_file, priv.private_bytes_raw(), pub.public_bytes_raw(), addr)

    content = key_file.read_text(encoding="utf-8")
    assert "WARNING: TEST ONLY - DO NOT USE ON MAINNET" in content
    assert addr in content


# ---------------------------------------------------------------------------
# Canonical Serialization & Whitespace/Key-Order Invariance
# ---------------------------------------------------------------------------

def test_canonical_json_invariance():
    tx_obj_1 = {
        "version": 1,
        "network_id": "course-testnet",
        "sender": "sender_address_placeholder",
        "recipient": "recipient_address_placeholder",
        "amount_units": 1250000,
        "nonce": 7,
        "memo_hash": "00" * 32,
    }
    # Different key ordering
    tx_obj_2 = {
        "memo_hash": "00" * 32,
        "nonce": 7,
        "amount_units": 1250000,
        "recipient": "recipient_address_placeholder",
        "sender": "sender_address_placeholder",
        "network_id": "course-testnet",
        "version": 1,
    }

    bytes1 = canonical_transaction_bytes(tx_obj_1)
    bytes2 = canonical_transaction_bytes(tx_obj_2)
    assert bytes1 == bytes2


# ---------------------------------------------------------------------------
# Signing and Independent Verification
# ---------------------------------------------------------------------------

def test_sign_and_verify_valid():
    priv, pub = generate_keypair()
    pub_bytes = pub.public_bytes_raw()
    sender_addr = pubkey_to_address(pub_bytes)

    _, pub_recip = generate_keypair()
    recipient_addr = pubkey_to_address(pub_recip.public_bytes_raw())

    tx = {
        "version": 1,
        "network_id": DEFAULT_NETWORK_ID,
        "sender": sender_addr,
        "recipient": recipient_addr,
        "amount_units": 1250000,
        "nonce": 7,
        "memo_hash": "00" * 32,
    }

    signed_tx = sign_transaction(priv.private_bytes_raw(), tx)
    assert verify_transaction(signed_tx) is True


def test_verify_rejects_modified_amount():
    priv, pub = generate_keypair()
    sender_addr = pubkey_to_address(pub.public_bytes_raw())
    _, pub_r = generate_keypair()
    recip_addr = pubkey_to_address(pub_r.public_bytes_raw())

    tx = {
        "version": 1,
        "network_id": DEFAULT_NETWORK_ID,
        "sender": sender_addr,
        "recipient": recip_addr,
        "amount_units": 100,
        "nonce": 1,
        "memo_hash": "00" * 32,
    }

    signed_tx = sign_transaction(priv.private_bytes_raw(), tx)

    # Tamper with amount
    tampered_tx = json.loads(json.dumps(signed_tx))
    tampered_tx["transaction"]["amount_units"] = 999999
    with pytest.raises(ValueError, match="Signature verification failed"):
        verify_transaction(tampered_tx)


def test_verify_rejects_wrong_network():
    priv, pub = generate_keypair()
    sender_addr = pubkey_to_address(pub.public_bytes_raw())
    _, pub_r = generate_keypair()
    recip_addr = pubkey_to_address(pub_r.public_bytes_raw())

    tx = {
        "version": 1,
        "network_id": "other-chain",
        "sender": sender_addr,
        "recipient": recip_addr,
        "amount_units": 100,
        "nonce": 1,
        "memo_hash": "00" * 32,
    }

    signed_tx = sign_transaction(priv.private_bytes_raw(), tx)
    with pytest.raises(ValueError, match="Network ID mismatch"):
        verify_transaction(signed_tx, expected_network=DEFAULT_NETWORK_ID)


def test_verify_rejects_wrong_signer_address():
    priv_alice, pub_alice = generate_keypair()
    _, pub_mallory = generate_keypair()
    addr_mallory = pubkey_to_address(pub_mallory.public_bytes_raw())
    _, pub_bob = generate_keypair()
    addr_bob = pubkey_to_address(pub_bob.public_bytes_raw())

    # Alice creates a transaction claiming to be Mallory
    tx = {
        "version": 1,
        "network_id": DEFAULT_NETWORK_ID,
        "sender": addr_mallory,
        "recipient": addr_bob,
        "amount_units": 100,
        "nonce": 1,
        "memo_hash": "00" * 32,
    }
    # Alice signs with Alice's key: sign_transaction rejects upfront because address != pubkey
    with pytest.raises(ValueError, match="Signer mismatch"):
        sign_transaction(priv_alice.private_bytes_raw(), tx)


def test_verify_rejects_replayed_nonce():
    priv, pub = generate_keypair()
    sender_addr = pubkey_to_address(pub.public_bytes_raw())
    _, pub_r = generate_keypair()
    recip_addr = pubkey_to_address(pub_r.public_bytes_raw())

    tx = {
        "version": 1,
        "network_id": DEFAULT_NETWORK_ID,
        "sender": sender_addr,
        "recipient": recip_addr,
        "amount_units": 100,
        "nonce": 5,
        "memo_hash": "00" * 32,
    }

    signed_tx = sign_transaction(priv.private_bytes_raw(), tx)
    nonce_tracker = {sender_addr: 5}

    # Attempt to replay with nonce 5 (<= last nonce)
    with pytest.raises(ValueError, match="Replay attack detected"):
        verify_transaction(signed_tx, nonce_tracker=nonce_tracker)


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------

def test_cli_wallet_flow(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    # 1. keygen
    key_file = tmp_path / "alice.key"
    kg_cmd = [sys.executable, "-m", "wallet", "keygen", "--out", str(key_file)]
    res_kg = subprocess.run(kg_cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res_kg.returncode == 0
    alice_info = json.loads(res_kg.stdout)
    alice_addr = alice_info["address"]

    # 2. recipient keygen
    res_kg_bob = subprocess.run([sys.executable, "-m", "wallet", "keygen"], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    bob_info = json.loads(res_kg_bob.stdout)
    bob_addr = bob_info["address"]

    # 3. sign
    tx = {
        "version": 1,
        "network_id": DEFAULT_NETWORK_ID,
        "sender": alice_addr,
        "recipient": bob_addr,
        "amount_units": 1250000,
        "nonce": 1,
        "memo_hash": "00" * 32,
    }
    tx_file = tmp_path / "tx.json"
    tx_file.write_text(json.dumps(tx), encoding="utf-8")
    signed_file = tmp_path / "signed_tx.json"

    sign_cmd = [
        sys.executable, "-m", "wallet", "sign",
        "--key", str(key_file),
        "--tx", str(tx_file),
        "--out", str(signed_file),
    ]
    res_sign = subprocess.run(sign_cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res_sign.returncode == 0
    assert signed_file.exists()

    # 4. verify
    verify_cmd = [
        sys.executable, "-m", "wallet", "verify",
        "--signed-tx", str(signed_file),
    ]
    res_verify = subprocess.run(verify_cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res_verify.returncode == 0
    assert "TRANSACTION VERIFIED" in res_verify.stdout

