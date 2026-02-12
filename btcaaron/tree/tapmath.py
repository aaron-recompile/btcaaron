"""
btcaaron.tree.tapmath - Pure Taproot math (no bitcoin-utils)

BIP 340/341 tagged hashes, tapleaf/tapbranch hashes, Merkle tree,
and control block construction. Standard library only (hashlib, struct).
"""

import hashlib
import struct
from typing import List, Tuple

# Tapscript leaf version per BIP 342
LEAF_VERSION = 0xC0


def tagged_hash(tag: str, data: bytes) -> bytes:
    """
    BIP 340 tagged hash: SHA256(SHA256(tag) || SHA256(tag) || data)
    """
    tag_digest = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_digest + tag_digest + data).digest()


def compact_size(n: int) -> bytes:
    """
    Bitcoin variable-length integer encoding.
    """
    if n < 0xFD:
        return struct.pack("<B", n)
    elif n <= 0xFFFF:
        return struct.pack("<BH", 0xFD, n)
    elif n <= 0xFFFFFFFF:
        return struct.pack("<BI", 0xFE, n)
    else:
        return struct.pack("<BQ", 0xFF, n)


def tapleaf_hash(script: bytes, leaf_version: int = LEAF_VERSION) -> bytes:
    """
    BIP 341 tapleaf hash: TaggedHash("TapLeaf", leaf_version || compact_size(len) || script)
    """
    payload = bytes([leaf_version]) + compact_size(len(script)) + script
    return tagged_hash("TapLeaf", payload)


def tapbranch_hash(left: bytes, right: bytes) -> bytes:
    """
    BIP 341 tapbranch hash. Inputs must be 32-byte hashes.
    Hashes are combined in lexicographic order.
    """
    if len(left) != 32 or len(right) != 32:
        raise ValueError("tapbranch_hash requires 32-byte inputs")
    if left > right:
        left, right = right, left
    return tagged_hash("TapBranch", left + right)


def compute_merkle_root(leaf_hashes: List[bytes]) -> bytes:
    """
    Build Taproot Merkle tree from leaf hashes.
    Returns 32-byte merkle root (or single leaf's hash if only one).
    """
    if not leaf_hashes:
        raise ValueError("Need at least one leaf")
    for h in leaf_hashes:
        if len(h) != 32:
            raise ValueError(f"Leaf hash must be 32 bytes, got {len(h)}")

    level = list(leaf_hashes)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                next_level.append(tapbranch_hash(level[i], level[i + 1]))
            else:
                next_level.append(level[i])
        level = next_level
    return level[0]


def compute_merkle_proof(leaf_hashes: List[bytes], leaf_index: int) -> List[bytes]:
    """
    Compute Merkle proof (sibling path) for leaf at leaf_index.
    Returns list of 32-byte hashes from leaf to root.
    """
    if leaf_index < 0 or leaf_index >= len(leaf_hashes):
        raise ValueError(f"leaf_index {leaf_index} out of range for {len(leaf_hashes)} leaves")

    level = list(leaf_hashes)
    proof = []

    while len(level) > 1:
        # Add sibling to proof (if we have one; odd-one-out has no sibling)
        if leaf_index % 2 == 0:  # we're left child
            sibling_idx = leaf_index + 1
            if sibling_idx < len(level):
                proof.append(level[sibling_idx])
        else:  # we're right child
            proof.append(level[leaf_index - 1])

        # Build next level
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                next_level.append(tapbranch_hash(level[i], level[i + 1]))
            else:
                next_level.append(level[i])
        level = next_level
        leaf_index = leaf_index // 2

    return proof


def compute_control_block(
    internal_key_bytes: bytes,
    leaf_hashes: List[bytes],
    leaf_index: int,
    is_odd: bool,
    leaf_version: int = LEAF_VERSION,
) -> bytes:
    """
    Build control block bytes for script path spend.
    internal_key_bytes: 32-byte x-only pubkey
    leaf_hashes: list of tapleaf hashes (same order as tree)
    leaf_index: which leaf is being spent
    is_odd: output key Y parity (1 if odd, 0 if even)
    """
    if len(internal_key_bytes) != 32:
        raise ValueError("internal_key must be 32 bytes")
    proof = compute_merkle_proof(leaf_hashes, leaf_index)
    version_byte = (leaf_version & 0xFE) | (1 if is_odd else 0)
    return bytes([version_byte]) + internal_key_bytes + b"".join(proof)
