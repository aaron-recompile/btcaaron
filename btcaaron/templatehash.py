"""
BIP 446 — OP_TEMPLATEHASH (Tapscript-only, opcode 0xce).

Implements the template hash per https://github.com/bitcoin/bips/blob/master/bip-0446.md :

    TaggedHash("TemplateHash",
        nVersion(4) || nLockTime(4) || sha_sequences(32) || sha_outputs(32)
        || annex_present(1) || input_index(4) [|| sha_annex(32)])

Deliberately omitted vs the BIP341 signature message: hash_type, spend_type, sha_prevouts,
sha_amounts, sha_scriptpubkeys. The hash therefore commits to the whole spending transaction
except which coins it spends — signatures over it (via OP_CHECKSIGFROMSTACK) are rebindable.

Cross-checked against bitcoin-inquisition v29.4-inq
(GenericTransactionSignatureChecker::GetTemplateHash, src/script/interpreter.cpp).
"""

from __future__ import annotations

import hashlib
import struct
from typing import Optional, Sequence, Tuple

OP_TEMPLATEHASH = 0xCE


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def tagged_hash(tag: str, msg: bytes) -> bytes:
    t = _sha256(tag.encode())
    return _sha256(t + t + msg)


def _compact_size(n: int) -> bytes:
    if n < 253:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)


def sha_sequences(sequences: Sequence[int]) -> bytes:
    """BIP341 sha_sequences: SHA256 of all input nSequence values (4-byte LE each)."""
    return _sha256(b"".join(struct.pack("<I", s) for s in sequences))


def sha_outputs(outputs: Sequence[Tuple[int, bytes]]) -> bytes:
    """BIP341 sha_outputs: SHA256 of all outputs in CTxOut format (amount || compact_size || spk)."""
    return _sha256(b"".join(struct.pack("<q", amt) + _compact_size(len(spk)) + spk for amt, spk in outputs))


def template_msg(version: int, locktime: int, sequences: Sequence[int],
                 outputs: Sequence[Tuple[int, bytes]], input_index: int = 0,
                 annex: Optional[bytes] = None) -> bytes:
    """The pre-image that OP_TEMPLATEHASH hashes (72 bytes + 5, or + 37 with an annex)."""
    msg = struct.pack("<I", version) + struct.pack("<I", locktime)
    msg += sha_sequences(sequences) + sha_outputs(outputs)
    msg += bytes([1 if annex is not None else 0])
    msg += struct.pack("<I", input_index)
    if annex is not None:
        msg += _sha256(_compact_size(len(annex)) + annex)
    return msg


def template_hash(version: int, locktime: int, sequences: Sequence[int],
                  outputs: Sequence[Tuple[int, bytes]], input_index: int = 0,
                  annex: Optional[bytes] = None) -> bytes:
    """32-byte value OP_TEMPLATEHASH pushes for this (version, locktime, sequences, outputs, index)."""
    return tagged_hash("TemplateHash", template_msg(version, locktime, sequences, outputs, input_index, annex))
