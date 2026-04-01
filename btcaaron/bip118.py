"""
BIP 118 — SIGHASH_ANYPREVOUT for Taproot (script path).

Implements ``Msg118`` / ``Ext118`` and ``TaggedHash("TapSighash", 0x00 || Msg || Ext)``
per https://github.com/bitcoin/bips/blob/master/bip-0118.mediawiki

Use with **BIP118 public keys** in tapscript: ``0x01 || 32-byte x-only`` (33 bytes) before
``OP_CHECKSIG``. Signatures use Schnorr (BIP 340) with an explicit sighash byte (e.g. ``0x41``).

Constants:
  - ``SIGHASH_ANYPREVOUT`` — bit mask on ``hash_type`` (bits 6–7), value ``0x40``.
  - ``SIGHASH_ANYPREVOUTANYSCRIPT`` — ``0xc0``.
  - ``SIGHASH_DEFAULT_APO`` — ``0x41`` = ``SIGHASH_ALL | SIGHASH_ANYPREVOUT`` (common case).
"""

from __future__ import annotations

import hashlib
import struct
from typing import Optional, Sequence

from bitcoinutils.constants import (
    LEAF_VERSION_TAPSCRIPT,
    SIGHASH_NONE,
    SIGHASH_SINGLE,
)
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction
from bitcoinutils.utils import prepend_compact_size, tagged_hash

# --- BIP118 hash_type bits (see BIP118) ---
SIGHASH_ANYPREVOUT = 0x40
SIGHASH_ANYPREVOUTANYSCRIPT = 0xC0

# Default explicit sighash: ALL (0x01) + ANYPREVOUT (0x40)
SIGHASH_DEFAULT_APO = 0x41

# BIP118 extension: key_version for APO signatures (not 0x00 like BIP342)
BIP118_KEY_VERSION = 0x01


def apo_pubkey_bytes(xonly_32: bytes) -> bytes:
    """33-byte BIP118 pubkey pushed before OP_CHECKSIG: ``0x01 || xonly``."""
    if len(xonly_32) != 32:
        raise ValueError("x-only pubkey must be 32 bytes")
    return b"\x01" + xonly_32


def _serialize_spk_ctxout(script_pubkey: Script) -> bytes:
    """scriptPubKey as in CTxOut: compact_size || script (P2TR is 35 bytes total)."""
    raw = script_pubkey.to_bytes()
    return prepend_compact_size(raw)


def _sha_outputs(tx: Transaction) -> bytes:
    h = b""
    for txout in tx.outputs:
        amount_bytes = struct.pack("<Q", txout.amount)
        script_bytes = txout.script_pubkey.to_bytes()
        h += amount_bytes + struct.pack("B", len(script_bytes)) + script_bytes
    return hashlib.sha256(h).digest()


def _sha_single_output(tx: Transaction, txin_index: int) -> bytes:
    txout = tx.outputs[txin_index]
    amount_bytes = struct.pack("<Q", txout.amount)
    script_bytes = txout.script_pubkey.to_bytes()
    blob = amount_bytes + struct.pack("B", len(script_bytes)) + script_bytes
    return hashlib.sha256(blob).digest()


def msg118(
    tx: Transaction,
    txin_index: int,
    script_pubkeys: Sequence[Script],
    amounts: Sequence[int],
    hash_type: int,
    annex: Optional[bytes] = None,
) -> bytes:
    """
    BIP118 ``Msg118(hash_type)`` (transaction half; extension is separate).
    """
    if hash_type & 0x40 == 0:
        raise ValueError("msg118 requires ANYPREVOUT-style hash_type (bit 0x40 set)")

    sighash_none = (hash_type & 0x03) == SIGHASH_NONE
    sighash_single = (hash_type & 0x03) == SIGHASH_SINGLE

    msg = bytes()
    msg += bytes([hash_type])
    msg += tx.version
    msg += tx.locktime

    if not sighash_none and not sighash_single:
        msg += _sha_outputs(tx)

    annex_present = annex is not None
    spend_type = 3 if annex_present else 2
    msg += bytes([spend_type])

    apo_mode = hash_type & 0xC0
    if apo_mode == SIGHASH_ANYPREVOUT:  # 0x40 — commit amount + scriptPubKey
        msg += int(amounts[txin_index]).to_bytes(8, "little")
        spk_ser = _serialize_spk_ctxout(script_pubkeys[txin_index])
        msg += spk_ser
    elif apo_mode == SIGHASH_ANYPREVOUTANYSCRIPT:
        pass  # omit amount and scriptPubKey
    else:
        raise ValueError(f"unsupported hash_type top bits: 0x{apo_mode:02x}")

    msg += tx.inputs[txin_index].sequence

    if annex_present:
        ann = prepend_compact_size(annex)
        msg += hashlib.sha256(ann).digest()

    if sighash_single:
        msg += _sha_single_output(tx, txin_index)

    return msg


def ext118(
    tapleaf_script: Script,
    hash_type: int,
) -> bytes:
    """
    BIP118 ``Ext118(hash_type)`` (tapleaf + key_version + codeseparator).
    """
    ext = b""
    apo_top = hash_type & 0xC0
    if apo_top != SIGHASH_ANYPREVOUTANYSCRIPT:
        leaf_bytes = tapleaf_script.to_bytes()
        tapleaf_hash = tagged_hash(
            bytes([LEAF_VERSION_TAPSCRIPT]) + prepend_compact_size(leaf_bytes),
            "TapLeaf",
        )
        ext += tapleaf_hash
    ext += bytes([BIP118_KEY_VERSION])
    ext += (0xFFFFFFFF).to_bytes(4, "little")
    return ext


def bip118_sighash(
    tx: Transaction,
    txin_index: int,
    script_pubkeys: Sequence[Script],
    amounts: Sequence[int],
    tapleaf_script: Script,
    hash_type: int = SIGHASH_DEFAULT_APO,
    annex: Optional[bytes] = None,
) -> bytes:
    """
    32-byte digest passed to BIP340 ``Verify`` for a BIP118 script-path signature.

    ``TaggedHash("TapSighash", 0x00 || Msg118 || Ext118)``.
    """
    m = msg118(tx, txin_index, script_pubkeys, amounts, hash_type, annex=annex)
    e = ext118(tapleaf_script, hash_type)
    preimage = b"\x00" + m + e
    return tagged_hash(preimage, "TapSighash")


def apo_digest_same_for_different_prevouts(
    tx_a: Transaction,
    tx_b: Transaction,
    txin_index: int,
    script_pubkeys: Sequence[Script],
    amounts: Sequence[int],
    tapleaf_script: Script,
    hash_type: int = SIGHASH_DEFAULT_APO,
) -> bool:
    """
    Property check: for ANYPREVOUT, changing only the spent outpoint (same amounts/spks/outputs)
    must yield the same digest.
    """
    d1 = bip118_sighash(
        tx_a, txin_index, script_pubkeys, amounts, tapleaf_script, hash_type
    )
    d2 = bip118_sighash(
        tx_b, txin_index, script_pubkeys, amounts, tapleaf_script, hash_type
    )
    return d1 == d2
