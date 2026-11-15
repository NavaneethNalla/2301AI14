"""
merkle: Merkle Trees and Proofs of Inclusion
Assignment 2 - IIT Patna CSE Blockchain Course
"""

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

__all__ = [
    "DOMAIN_LEAF",
    "DOMAIN_NODE",
    "hash_leaf",
    "hash_node",
    "get_empty_tree_root",
    "MerkleTree",
    "get_expected_sibling_count",
    "verify_proof",
]

