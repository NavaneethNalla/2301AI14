"""
Unit and integration tests for merkle (Assignment 2).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

from merkle.core import (
    DOMAIN_LEAF,
    DOMAIN_NODE,
    MerkleTree,
    get_empty_tree_root,
    get_expected_sibling_count,
    hash_leaf,
    hash_node,
    verify_proof,
)


# ---------------------------------------------------------------------------
# Domain Separation and Elementary Construction
# ---------------------------------------------------------------------------

def test_leaf_and_node_domain_separation():
    data = b"test_data"
    h_l = hash_leaf(data)
    expected_leaf = hashlib.sha256(b"\x00" + data).digest()
    assert h_l == expected_leaf

    left = b"\x11" * 32
    right = b"\x22" * 32
    h_n = hash_node(left, right)
    expected_node = hashlib.sha256(b"\x01" + left + right).digest()
    assert h_n == expected_node


def test_empty_tree():
    tree = MerkleTree([])
    assert tree.root == get_empty_tree_root()
    assert tree.root_hex == hashlib.sha256(b"").hexdigest()


def test_single_leaf_tree():
    data = b"tx0"
    tree = MerkleTree([data])
    assert tree.root == hash_leaf(data)
    proof = tree.get_proof(0)
    assert proof["tree_size"] == 1
    assert proof["leaf_index"] == 0
    assert len(proof["siblings"]) == 0
    assert verify_proof(data, proof, tree.root_hex) is True


def test_two_leaf_tree():
    d0 = b"tx0"
    d1 = b"tx1"
    tree = MerkleTree([d0, d1])
    h0 = hash_leaf(d0)
    h1 = hash_leaf(d1)
    expected_root = hash_node(h0, h1)
    assert tree.root == expected_root

    proof0 = tree.get_proof(0)
    assert proof0["siblings"] == [{"side": "right", "hash": h1.hex()}]
    assert verify_proof(d0, proof0, tree.root_hex) is True

    proof1 = tree.get_proof(1)
    assert proof1["siblings"] == [{"side": "left", "hash": h0.hex()}]
    assert verify_proof(d1, proof1, tree.root_hex) is True


# ---------------------------------------------------------------------------
# Five-Leaf Tree and Detailed Proof Path
# ---------------------------------------------------------------------------

def test_five_leaf_tree_structure_and_proof():
    leaves = [f"tx_{i}".encode("ascii") for i in range(5)]
    tree = MerkleTree(leaves)

    # Verify proof for leaf_index: 2
    proof2 = tree.get_proof(2)
    assert proof2["leaf_index"] == 2
    assert proof2["tree_size"] == 5

    # Check sibling sequence directions
    sides = [s["side"] for s in proof2["siblings"]]
    assert sides == ["right", "left", "right"]

    assert verify_proof(leaves[2], proof2, tree.root_hex) is True

    # Verify every leaf in the 5-leaf tree generates a valid proof
    for i in range(5):
        p = tree.get_proof(i)
        assert verify_proof(leaves[i], p, tree.root_hex) is True


# ---------------------------------------------------------------------------
# Arbitrary Sizes & Inclusion Verification Loop
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 7, 8, 15, 16, 31, 32, 50])
def test_all_leaves_verify_across_sizes(size):
    leaves = [f"leaf_data_{i}".encode("utf-8") for i in range(size)]
    tree = MerkleTree(leaves)
    for i in range(size):
        proof = tree.get_proof(i)
        assert verify_proof(leaves[i], proof, tree.root_hex) is True


# ---------------------------------------------------------------------------
# Strict Verification & Tamper Detection
# ---------------------------------------------------------------------------

def test_verify_rejects_tampered_leaf():
    leaves = [b"Alice pays Bob 10", b"Charlie pays Dave 20"]
    tree = MerkleTree(leaves)
    proof0 = tree.get_proof(0)
    # Attempt verification with altered leaf data
    assert verify_proof(b"Alice pays Bob 99", proof0, tree.root_hex) is False


def test_verify_rejects_wrong_root():
    leaves = [b"a", b"b"]
    tree = MerkleTree(leaves)
    proof0 = tree.get_proof(0)
    fake_root = "00" * 32
    assert verify_proof(b"a", proof0, fake_root) is False


def test_verify_rejects_invalid_root_hex():
    leaves = [b"a", b"b"]
    tree = MerkleTree(leaves)
    proof0 = tree.get_proof(0)
    with pytest.raises(ValueError, match="expected_root must be 64 hex"):
        verify_proof(b"a", proof0, "1234abcd")  # Too short


def test_verify_rejects_out_of_range_leaf_index():
    proof = {"leaf_index": 5, "tree_size": 5, "siblings": []}
    with pytest.raises(ValueError, match="out of range"):
        verify_proof(b"a", proof, "00" * 32)


def test_verify_rejects_invalid_sibling_side():
    proof = {
        "leaf_index": 0,
        "tree_size": 2,
        "siblings": [{"side": "upward", "hash": "aa" * 32}],
    }
    with pytest.raises(ValueError, match="Invalid sibling direction"):
        verify_proof(b"a", proof, "00" * 32)


def test_verify_rejects_malformed_sibling_hash():
    proof = {
        "leaf_index": 0,
        "tree_size": 2,
        "siblings": [{"side": "right", "hash": "not-valid-hex"}],
    }
    with pytest.raises(ValueError, match="Sibling 0 hash must be 64 hex characters"):
        verify_proof(b"a", proof, "00" * 32)


def test_verify_rejects_unnecessarily_long_or_short_proof():
    leaves = [b"a", b"b", b"c", b"d"]
    tree = MerkleTree(leaves)
    proof0 = tree.get_proof(0)
    assert len(proof0["siblings"]) == 2

    # Injected extra sibling
    tampered_long = json.loads(json.dumps(proof0))
    tampered_long["siblings"].append({"side": "right", "hash": "aa" * 32})
    with pytest.raises(ValueError, match="Invalid proof length"):
        verify_proof(b"a", tampered_long, tree.root_hex)

    # Truncated sibling
    tampered_short = json.loads(json.dumps(proof0))
    tampered_short["siblings"].pop()
    with pytest.raises(ValueError, match="Invalid proof length"):
        verify_proof(b"a", tampered_short, tree.root_hex)


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------

def test_cli_root_and_prove_and_verify(tmp_path):
    # Setup test file
    leaf_file = tmp_path / "leaves.txt"
    leaf_file.write_text("tx1\ntx2\ntx3\ntx4\ntx5\n", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    root_cmd = [sys.executable, "-m", "merkle", "root", "--file", str(leaf_file)]
    res_root = subprocess.run(root_cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res_root.returncode == 0
    assert "tree_size: 5" in res_root.stdout
    root_hex = res_root.stdout.strip().split("root: ")[1]

    # Generate proof for index 2
    proof_file = tmp_path / "proof.json"
    prove_cmd = [
        sys.executable, "-m", "merkle", "prove",
        "--index", "2",
        "--file", str(leaf_file),
        "--out", str(proof_file),
    ]
    res_prove = subprocess.run(prove_cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res_prove.returncode == 0
    assert proof_file.exists()

    # Verify proof via CLI
    verify_cmd = [
        sys.executable, "-m", "merkle", "verify",
        "--leaf", "tx3",
        "--proof", str(proof_file),
        "--root", root_hex,
    ]
    res_verify = subprocess.run(verify_cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent), env=env)
    assert res_verify.returncode == 0
    assert "VERIFICATION SUCCESS" in res_verify.stdout

