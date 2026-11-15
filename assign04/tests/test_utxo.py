"""
Unit and integration tests for utxo (Assignment 4).
Contains at least 20 comprehensive unit tests covering all acceptance and rejection rules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

from cryptography.hazmat.primitives.asymmetric import ed25519

from utxo.ledger import Ledger
from utxo.models import (
    OutPoint,
    Transaction,
    TxInput,
    TxOutput,
    compute_pubkey_hash,
)


@pytest.fixture
def keypair_alice():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()
    pkh = compute_pubkey_hash(pub)
    return priv, pub, pkh


@pytest.fixture
def keypair_bob():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()
    pkh = compute_pubkey_hash(pub)
    return priv, pub, pkh


# ---------------------------------------------------------------------------
# Test 1 & 2: Alice-Pays-Bob Canonical Scenario & Double Spend
# ---------------------------------------------------------------------------

def test_1_alice_pays_bob_scenario(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob

    ledger = Ledger()
    op40 = OutPoint(tx_id="11" * 32, output_index=0)
    op70 = OutPoint(tx_id="22" * 32, output_index=1)
    ledger.add_utxo(op40, TxOutput(value=40, pubkey_hash=pkh_a))
    ledger.add_utxo(op70, TxOutput(value=70, pubkey_hash=pkh_a))

    # Alice pays Bob 85 with fee 2 -> consumes 70 + 40 = 110, creates 85 (Bob) and 23 (Alice change)
    tx = ledger.build_and_sign_transaction(
        priv_key_bytes=priv_a.private_bytes_raw(),
        recipient_pubkey_hash=pkh_b,
        amount=85,
        fee=2,
    )

    success, fee, reason = ledger.apply_transaction(tx)
    assert success is True
    assert fee == 2
    assert reason == "ACCEPTED"

    # Previous UTXOs consumed
    assert ledger.get_utxo(op40) is None
    assert ledger.get_utxo(op70) is None

    # New UTXOs created
    out_bob = ledger.get_utxo(OutPoint(tx.tx_id, 0))
    out_alice_change = ledger.get_utxo(OutPoint(tx.tx_id, 1))

    assert out_bob is not None
    assert out_bob.value == 85
    assert out_bob.pubkey_hash == pkh_b

    assert out_alice_change is not None
    assert out_alice_change.value == 23
    assert out_alice_change.pubkey_hash == pkh_a


def test_2_double_spend_same_transaction_twice(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob

    ledger = Ledger()
    op = OutPoint(tx_id="33" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=50, pubkey_hash=pkh_a))

    tx = ledger.build_and_sign_transaction(
        priv_key_bytes=priv_a.private_bytes_raw(),
        recipient_pubkey_hash=pkh_b,
        amount=30,
        fee=5,
    )

    # First submission succeeds
    ok1, fee1, _ = ledger.apply_transaction(tx)
    assert ok1 is True
    assert fee1 == 5

    # Second submission of identical transaction MUST fail
    ok2, fee2, reason2 = ledger.apply_transaction(tx)
    assert ok2 is False
    assert fee2 == 0
    assert "REJECT_MISSING_UTXO" in reason2


def test_3_double_spend_competing_transactions(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    _, pub_c = ed25519.Ed25519PrivateKey.generate().public_key(), ed25519.Ed25519PrivateKey.generate().public_key()
    pkh_charlie = compute_pubkey_hash(pub_c.public_bytes_raw())

    ledger = Ledger()
    op = OutPoint(tx_id="44" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=100, pubkey_hash=pkh_a))

    # tx1 pays Bob 60
    tx1 = ledger.build_and_sign_transaction(priv_a.private_bytes_raw(), pkh_b, 60, 5)

    # Reset ledger to recreate competing tx2 spending the exact same UTXO to Charlie
    tx2 = ledger.build_and_sign_transaction(priv_a.private_bytes_raw(), pkh_charlie, 40, 5)

    # Apply tx1
    ok1, _, _ = ledger.apply_transaction(tx1)
    assert ok1 is True

    # Apply tx2 -> must fail because op was already spent
    ok2, _, reason2 = ledger.apply_transaction(tx2)
    assert ok2 is False
    assert "REJECT_MISSING_UTXO" in reason2


# ---------------------------------------------------------------------------
# Tests 4 - 10: Structural & Range Rejections
# ---------------------------------------------------------------------------

def test_4_reject_nonexistent_input(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()

    fake_op = OutPoint(tx_id="ff" * 32, output_index=9)
    inp = TxInput(prev_tx_id=fake_op.tx_id, prev_out_index=fake_op.output_index)
    out = TxOutput(value=10, pubkey_hash=pkh_b)
    tx = Transaction(inputs=[inp], outputs=[out])

    # Sign input
    sh = tx.compute_sighash(0)
    sig = priv_a.sign(sh)
    tx.inputs[0].signature_hex = sig.hex()
    tx.inputs[0].pubkey_hex = pub_a.hex()

    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_MISSING_UTXO" in reason


def test_5_reject_duplicate_inputs_within_same_tx(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op = OutPoint(tx_id="55" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=100, pubkey_hash=pkh_a))

    inp1 = TxInput(prev_tx_id=op.tx_id, prev_out_index=op.output_index)
    inp2 = TxInput(prev_tx_id=op.tx_id, prev_out_index=op.output_index)
    out = TxOutput(value=50, pubkey_hash=pkh_b)
    tx = Transaction(inputs=[inp1, inp2], outputs=[out])

    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_DUPLICATE_INPUT" in reason


def test_6_reject_empty_inputs():
    ledger = Ledger()
    tx = Transaction(inputs=[], outputs=[TxOutput(value=10, pubkey_hash="aa" * 20)])
    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_EMPTY_INPUTS" in reason


def test_7_reject_empty_outputs():
    ledger = Ledger()
    tx = Transaction(inputs=[TxInput(prev_tx_id="00" * 32, prev_out_index=0)], outputs=[])
    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_EMPTY_OUTPUTS" in reason


def test_8_reject_negative_output_value():
    with pytest.raises(ValueError, match="Output value must be positive"):
        TxOutput(value=-50, pubkey_hash="aa" * 20)


def test_9_reject_zero_output_value():
    with pytest.raises(ValueError, match="Output value must be positive"):
        TxOutput(value=0, pubkey_hash="aa" * 20)


def test_10_reject_value_creation_out_of_thin_air(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op = OutPoint(tx_id="66" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=10, pubkey_hash=pkh_a))

    # Inputs = 10, Outputs = 100
    inp = TxInput(prev_tx_id=op.tx_id, prev_out_index=op.output_index)
    out = TxOutput(value=100, pubkey_hash=pkh_b)
    tx = Transaction(inputs=[inp], outputs=[out])

    sh = tx.compute_sighash(0)
    tx.inputs[0].signature_hex = priv_a.sign(sh).hex()
    tx.inputs[0].pubkey_hex = pub_a.hex()

    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_VALUE_CREATION" in reason


# ---------------------------------------------------------------------------
# Tests 11 - 16: Cryptographic Locks, Atomicity & Fees
# ---------------------------------------------------------------------------

def test_11_zero_fee_transaction_accepted(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op = OutPoint(tx_id="77" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=25, pubkey_hash=pkh_a))

    # Consumes 25, outputs 25 -> fee = 0
    tx = ledger.build_and_sign_transaction(priv_a.private_bytes_raw(), pkh_b, 25, 0)
    ok, fee, reason = ledger.apply_transaction(tx)
    assert ok is True
    assert fee == 0


def test_12_reject_p2pkh_lock_mismatch(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    priv_b, pub_b, pkh_b = keypair_bob
    ledger = Ledger()

    # UTXO is locked to Alice
    op = OutPoint(tx_id="88" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=50, pubkey_hash=pkh_a))

    # Bob tries to spend Alice's UTXO with Bob's pubkey
    inp = TxInput(prev_tx_id=op.tx_id, prev_out_index=op.output_index)
    out = TxOutput(value=40, pubkey_hash=pkh_b)
    tx = Transaction(inputs=[inp], outputs=[out])

    sh = tx.compute_sighash(0)
    tx.inputs[0].signature_hex = priv_b.sign(sh).hex()
    tx.inputs[0].pubkey_hex = pub_b.hex()

    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_LOCK_MISMATCH" in reason


def test_13_reject_bad_cryptographic_signature(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op = OutPoint(tx_id="99" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=50, pubkey_hash=pkh_a))

    tx = ledger.build_and_sign_transaction(priv_a.private_bytes_raw(), pkh_b, 40, 5)

    # Corrupt 1 byte of signature
    sig_bytearray = bytearray.fromhex(tx.inputs[0].signature_hex)
    sig_bytearray[0] ^= 0xff
    tx.inputs[0].signature_hex = bytes(sig_bytearray).hex()

    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_BAD_SIGNATURE" in reason


def test_14_reject_malformed_pubkey_length(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op = OutPoint(tx_id="ab" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=50, pubkey_hash=pkh_a))

    tx = ledger.build_and_sign_transaction(priv_a.private_bytes_raw(), pkh_b, 40, 5)
    tx.inputs[0].pubkey_hex = "1234abcd"  # Invalid length

    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_MALFORMED_PUBKEY" in reason


def test_15_reject_malformed_signature_length(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op = OutPoint(tx_id="ac" * 32, output_index=0)
    ledger.add_utxo(op, TxOutput(value=50, pubkey_hash=pkh_a))

    tx = ledger.build_and_sign_transaction(priv_a.private_bytes_raw(), pkh_b, 40, 5)
    tx.inputs[0].signature_hex = "ffff"  # Invalid length

    ok, _, reason = ledger.apply_transaction(tx)
    assert ok is False
    assert "REJECT_MALFORMED_SIG" in reason


def test_16_atomic_state_preserved_on_failure(keypair_alice, keypair_bob):
    priv_a, pub_a, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op1 = OutPoint(tx_id="ba" * 32, output_index=0)
    op2 = OutPoint(tx_id="bb" * 32, output_index=1)
    ledger.add_utxo(op1, TxOutput(value=10, pubkey_hash=pkh_a))
    ledger.add_utxo(op2, TxOutput(value=20, pubkey_hash=pkh_a))

    initial_snapshot = dict(ledger.utxos)

    # Attempt invalid transaction (insufficient input value for output)
    inp = TxInput(prev_tx_id=op1.tx_id, prev_out_index=op1.output_index)
    out = TxOutput(value=50, pubkey_hash=pkh_b)
    bad_tx = Transaction(inputs=[inp], outputs=[out])
    sh = bad_tx.compute_sighash(0)
    bad_tx.inputs[0].signature_hex = priv_a.sign(sh).hex()
    bad_tx.inputs[0].pubkey_hex = pub_a.hex()

    ok, _, _ = ledger.apply_transaction(bad_tx)
    assert ok is False

    # State must be 100% unchanged
    assert ledger.utxos == initial_snapshot


# ---------------------------------------------------------------------------
# Tests 17 - 21: Coin Selection, Snapshots, and OutPoints
# ---------------------------------------------------------------------------

def test_17_coin_selection_largest_first(keypair_alice):
    _, _, pkh_a = keypair_alice
    ledger = Ledger()
    op_10 = OutPoint(tx_id="01" * 32, output_index=0)
    op_50 = OutPoint(tx_id="02" * 32, output_index=0)
    op_30 = OutPoint(tx_id="03" * 32, output_index=0)
    ledger.add_utxo(op_10, TxOutput(value=10, pubkey_hash=pkh_a))
    ledger.add_utxo(op_50, TxOutput(value=50, pubkey_hash=pkh_a))
    ledger.add_utxo(op_30, TxOutput(value=30, pubkey_hash=pkh_a))

    # Need 35 units total (30 target + 5 fee)
    # Largest-first should pick 50 alone (50 >= 35) and leave 30 and 10 untouched
    selected, change = ledger.select_coins_largest_first(pkh_a, target_amount=30, fee=5)
    assert len(selected) == 1
    assert selected[0][0] == op_50
    assert change == 15  # 50 - 35 = 15


def test_18_coin_selection_deterministic_tie_breaker(keypair_alice):
    _, _, pkh_a = keypair_alice
    ledger = Ledger()
    # Two UTXOs with exact same value (20), but different tx_ids
    op_a = OutPoint(tx_id="0a" * 32, output_index=0)
    op_b = OutPoint(tx_id="0b" * 32, output_index=0)
    ledger.add_utxo(op_b, TxOutput(value=20, pubkey_hash=pkh_a))
    ledger.add_utxo(op_a, TxOutput(value=20, pubkey_hash=pkh_a))

    selected, change = ledger.select_coins_largest_first(pkh_a, target_amount=15, fee=2)
    assert len(selected) == 1
    # Tie-breaking picks lexicographically smaller tx_id first
    assert selected[0][0] == op_a


def test_19_coin_selection_insufficient_funds(keypair_alice):
    _, _, pkh_a = keypair_alice
    ledger = Ledger()
    ledger.add_utxo(OutPoint(tx_id="01" * 32, output_index=0), TxOutput(value=20, pubkey_hash=pkh_a))

    with pytest.raises(ValueError, match="Insufficient funds"):
        ledger.select_coins_largest_first(pkh_a, target_amount=100, fee=5)


def test_20_snapshot_save_and_reload(tmp_path, keypair_alice, keypair_bob):
    _, _, pkh_a = keypair_alice
    _, _, pkh_b = keypair_bob
    ledger = Ledger()
    op1 = OutPoint(tx_id="11" * 32, output_index=0)
    op2 = OutPoint(tx_id="22" * 32, output_index=1)
    ledger.add_utxo(op1, TxOutput(value=40, pubkey_hash=pkh_a))
    ledger.add_utxo(op2, TxOutput(value=85, pubkey_hash=pkh_b))

    snap_file = tmp_path / "snapshot.json"
    ledger.save_snapshot(snap_file)

    loaded_ledger = Ledger.load_snapshot(snap_file)
    assert len(loaded_ledger.utxos) == 2
    assert loaded_ledger.get_utxo(op1) == TxOutput(value=40, pubkey_hash=pkh_a)
    assert loaded_ledger.get_utxo(op2) == TxOutput(value=85, pubkey_hash=pkh_b)


def test_21_outpoint_string_roundtrip():
    op = OutPoint(tx_id="ab" * 32, output_index=3)
    s = op.to_str()
    op_recovered = OutPoint.from_str(s)
    assert op == op_recovered


def test_22_cli_demo_alice_bob():
    cmd = [sys.executable, "-m", "utxo", "demo-alice-bob"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res.returncode == 0
    assert "paying 85 to Bob with fee 2" in res.stdout
    assert "Double Spend Attack" in res.stdout
    assert "REJECT_MISSING_UTXO" in res.stdout
