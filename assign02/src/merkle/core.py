"""
merkle.core
===========
Deterministic Merkle Tree library implementing domain-separated SHA-256 leaf and
node hashing, unambiguous odd-leaf promotion, inclusion proof generation,
and independent strict verification.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

DOMAIN_LEAF = b"\x00"
DOMAIN_NODE = b"\x01"


def hash_leaf(data: bytes) -> bytes:
    """
    Computes domain-separated leaf hash:
    H_leaf = SHA256(0x00 || data)
    """
    return hashlib.sha256(DOMAIN_LEAF + data).digest()


def hash_node(left: bytes, right: bytes) -> bytes:
    """
    Computes domain-separated internal node hash:
    H_node = SHA256(0x01 || left || right)
    """
    if len(left) != 32 or len(right) != 32:
        raise ValueError("Internal node children must each be 32 bytes.")
    return hashlib.sha256(DOMAIN_NODE + left + right).digest()


def get_empty_tree_root() -> bytes:
    """
    Returns the deterministic root for an empty tree (zero leaves):
    SHA256(b"") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    """
    return hashlib.sha256(b"").digest()


class MerkleTree:
    """
    Full in-memory Merkle Tree with unambiguous odd-node promotion.
    """

    def __init__(self, leaves: List[bytes]) -> None:
        self.leaves = list(leaves)
        self.levels: List[List[bytes]] = []
        self._build_tree()

    def _build_tree(self) -> None:
        if not self.leaves:
            self.root = get_empty_tree_root()
            self.levels = [[]]
            return

        # Level 0: Leaf hashes
        current_level = [hash_leaf(leaf) for leaf in self.leaves]
        self.levels = [current_level]

        # Iteratively construct parent levels
        while len(current_level) > 1:
            next_level: List[bytes] = []
            n = len(current_level)
            for i in range(0, n, 2):
                if i + 1 < n:
                    next_level.append(hash_node(current_level[i], current_level[i + 1]))
                else:
                    # Unpaired odd node: promoted directly without re-hashing
                    next_level.append(current_level[i])
            current_level = next_level
            self.levels.append(current_level)

        self.root = self.levels[-1][0]

    @property
    def root_hex(self) -> str:
        return self.root.hex()

    def get_proof(self, leaf_index: int) -> Dict[str, Any]:
        """
        Generates an inclusion proof for the leaf at leaf_index.
        Returns a dictionary matching the required JSON format:
        {
          "leaf_index": int,
          "tree_size": int,
          "siblings": [
            {"side": "left" | "right", "hash": "64 hex chars"}, ...
          ]
        }
        """
        n_leaves = len(self.leaves)
        if leaf_index < 0 or leaf_index >= n_leaves:
            raise IndexError(
                f"leaf_index {leaf_index} out of range for tree of size {n_leaves}."
            )

        siblings: List[Dict[str, str]] = []
        idx = leaf_index

        for level_idx in range(len(self.levels) - 1):
            level = self.levels[level_idx]
            level_len = len(level)

            if idx % 2 == 0:
                # Current node is on left; partner is on right if available
                if idx + 1 < level_len:
                    siblings.append({"side": "right", "hash": level[idx + 1].hex()})
                # If idx + 1 >= level_len, this node was promoted, so no sibling at this level
                idx = idx // 2
            else:
                # Current node is on right; partner is on left
                siblings.append({"side": "left", "hash": level[idx - 1].hex()})
                idx = idx // 2

        return {
            "leaf_index": leaf_index,
            "tree_size": n_leaves,
            "siblings": siblings,
        }


def get_expected_sibling_count(leaf_index: int, tree_size: int) -> int:
    """
    Computes the exact number of siblings expected for a given leaf_index and tree_size
    under the unambiguous node-promotion rule.
    """
    if tree_size <= 0:
        raise ValueError("tree_size must be positive.")
    if leaf_index < 0 or leaf_index >= tree_size:
        raise ValueError("leaf_index out of bounds.")
    if tree_size == 1:
        return 0

    current_len = tree_size
    idx = leaf_index
    count = 0
    while current_len > 1:
        if idx % 2 == 0:
            if idx + 1 < current_len:
                count += 1
            idx = idx // 2
        else:
            count += 1
            idx = idx // 2
        current_len = (current_len + 1) // 2

    return count


def verify_proof(leaf_data: bytes, proof: Dict[str, Any], expected_root_hex: str) -> bool:
    """
    Independently verifies an inclusion proof using ONLY:
    - leaf_data: raw bytes of the target leaf
    - proof: proof dictionary containing leaf_index, tree_size, and siblings
    - expected_root_hex: 64 hexadecimal characters of expected root
    """
    # 1. Validate expected_root_hex
    clean_root_hex = expected_root_hex.strip().lower()
    if clean_root_hex.startswith("0x"):
        clean_root_hex = clean_root_hex[2:]
    if len(clean_root_hex) != 64:
        raise ValueError(f"expected_root must be 64 hex characters (32 bytes), got {len(clean_root_hex)}.")
    try:
        expected_root_bytes = bytes.fromhex(clean_root_hex)
    except ValueError as e:
        raise ValueError(f"Malformed expected_root hex: {e}") from e

    # 2. Validate proof top-level structure
    if not isinstance(proof, dict):
        raise ValueError("Proof must be a JSON object (dict).")
    for key in ("leaf_index", "tree_size", "siblings"):
        if key not in proof:
            raise ValueError(f"Proof missing required field: {key}")

    leaf_index = proof["leaf_index"]
    tree_size = proof["tree_size"]
    siblings = proof["siblings"]

    if not isinstance(leaf_index, int) or not isinstance(tree_size, int):
        raise ValueError("leaf_index and tree_size must be integers.")
    if tree_size <= 0:
        raise ValueError(f"Invalid tree_size: {tree_size}. Must be positive.")
    if leaf_index < 0 or leaf_index >= tree_size:
        raise ValueError(f"leaf_index {leaf_index} out of range for tree_size {tree_size}.")
    if not isinstance(siblings, list):
        raise ValueError("siblings must be a list.")

    # 3. Check for exact sibling count to prevent proof truncation or malleability
    expected_count = get_expected_sibling_count(leaf_index, tree_size)
    if len(siblings) != expected_count:
        raise ValueError(
            f"Invalid proof length: expected {expected_count} siblings for index {leaf_index} of {tree_size}, but got {len(siblings)}."
        )

    # 4. Compute starting leaf hash
    current_hash = hash_leaf(leaf_data)

    # 5. Ascend the proof path
    for i, item in enumerate(siblings):
        if not isinstance(item, dict):
            raise ValueError(f"Sibling {i} must be a dictionary.")
        if "side" not in item or "hash" not in item:
            raise ValueError(f"Sibling {i} missing 'side' or 'hash'.")

        side = item["side"]
        sibling_hex = item["hash"].strip().lower()
        if sibling_hex.startswith("0x"):
            sibling_hex = sibling_hex[2:]
        if len(sibling_hex) != 64:
            raise ValueError(f"Sibling {i} hash must be 64 hex characters, got {len(sibling_hex)}.")
        try:
            sibling_bytes = bytes.fromhex(sibling_hex)
        except ValueError as e:
            raise ValueError(f"Malformed sibling hash at index {i}: {e}") from e

        if side == "right":
            current_hash = hash_node(current_hash, sibling_bytes)
        elif side == "left":
            current_hash = hash_node(sibling_bytes, current_hash)
        else:
            raise ValueError(f"Invalid sibling direction '{side}' at index {i}. Must be 'left' or 'right'.")

    return current_hash == expected_root_bytes

