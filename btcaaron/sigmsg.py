"""
BIP 341 SigMsg raw preimage — the variable-length data fed to
``TaggedHash("TapSighash", preimage)`` during Taproot signature validation.

The preimage length depends on sighash flags::

    base = 174  (for key-path, SIGHASH_ALL, no annex)
    - is_anyonecanpay:  -49  (replace 4×32B hashes + 4B index with 36+8+var+4)
    - is_none:          -32  (sha_outputs omitted)
    + has_annex:        +32  (sha_annex added)

With the epoch byte (0x00) prepended:  base + 1 = 175 bytes for key-path ALL.

For script-path (ext_flag=1):  add 37 bytes (tapleaf_hash + key_version + codesep_pos).

This module exposes the raw preimage so CSFS experiments can use ``OP_SIZE``
to detect which sighash flag the signer used (Rubin's "Fun with CSFS" #3).

Reference:
    https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki#signature-validation-rules
"""

from __future__ import annotations

import hashlib
import struct
from typing import Optional, Sequence

from bitcoinutils.constants import (
    LEAF_VERSION_TAPSCRIPT,
    SIGHASH_ALL,
    SIGHASH_ANYONECANPAY,
    SIGHASH_NONE,
    SIGHASH_SINGLE,
    TAPROOT_SIGHASH_ALL,
)
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction
from bitcoinutils.utils import h_to_b, prepend_compact_size, tagged_hash


def compute_sigmsg_preimage(
    tx: Transaction,
    txin_index: int,
    script_pubkeys: Sequence[Script],
    amounts: Sequence[int],
    *,
    ext_flag: int = 0,
    script: Optional[Script] = None,
    leaf_ver: int = LEAF_VERSION_TAPSCRIPT,
    sighash: int = TAPROOT_SIGHASH_ALL,
) -> bytes:
    """
    Build the BIP 341 SigMsg preimage (the data before ``TaggedHash``).

    Returns the **raw bytes** that would be passed to
    ``tagged_hash(..., "TapSighash")`` to produce the 32-byte digest.

    Parameters
    ----------
    tx : Transaction
        The spending transaction (fully built, with inputs/outputs set).
    txin_index : int
        Index of the input being signed.
    script_pubkeys : list[Script]
        scriptPubKeys of ALL spent UTXOs (one per input).
    amounts : list[int]
        Amounts in satoshis of ALL spent UTXOs (one per input).
    ext_flag : int
        0 for key-path, 1 for script-path (BIP 342 extension).
    script : Script or None
        The tapleaf script being executed (required when ext_flag=1).
    leaf_ver : int
        Leaf version, default ``LEAF_VERSION_TAPSCRIPT`` (0xC0).
    sighash : int
        Sighash type (TAPROOT_SIGHASH_ALL, SIGHASH_NONE, etc.).

    Returns
    -------
    bytes
        Raw preimage: ``epoch || hash_type || nVersion || nLockTime || ...``
    """
    sighash_none = (sighash & 0x03) == SIGHASH_NONE
    sighash_single = (sighash & 0x03) == SIGHASH_SINGLE
    anyone_can_pay = (sighash & 0x80) == SIGHASH_ANYONECANPAY

    # epoch byte
    preimage = bytes([0])

    # sighash type
    preimage += bytes([sighash])

    # nVersion (4B LE)
    preimage += tx.version

    # nLockTime (4B LE)
    preimage += tx.locktime

    # --- Data about ALL inputs (omitted if ANYONECANPAY) ---
    if not anyone_can_pay:
        # sha_prevouts
        buf = b""
        for txin in tx.inputs:
            buf += h_to_b(txin.txid)[::-1] + struct.pack("<I", txin.txout_index)
        preimage += hashlib.sha256(buf).digest()

        # sha_amounts
        buf = b""
        for a in amounts:
            buf += int(a).to_bytes(8, "little")
        preimage += hashlib.sha256(buf).digest()

        # sha_scriptpubkeys
        buf = b""
        for spk in script_pubkeys:
            s = spk.to_hex()
            script_len = len(s) // 2
            buf += bytes([script_len]) + h_to_b(s)
        preimage += hashlib.sha256(buf).digest()

        # sha_sequences
        buf = b""
        for txin in tx.inputs:
            buf += txin.sequence
        preimage += hashlib.sha256(buf).digest()

    # --- sha_outputs (omitted if NONE or SINGLE) ---
    if not (sighash_none or sighash_single):
        buf = b""
        for txout in tx.outputs:
            amount_bytes = struct.pack("<Q", txout.amount)
            script_bytes = txout.script_pubkey.to_bytes()
            buf += amount_bytes + struct.pack("B", len(script_bytes)) + script_bytes
        preimage += hashlib.sha256(buf).digest()

    # --- spend_type ---
    spend_type = ext_flag * 2 + 0  # no annex support for now
    preimage += bytes([spend_type])

    # --- Data about THIS input ---
    if anyone_can_pay:
        txin = tx.inputs[txin_index]
        preimage += h_to_b(txin.txid)[::-1] + struct.pack("<I", txin.txout_index)
        preimage += int(amounts[txin_index]).to_bytes(8, "little")
        spk = script_pubkeys[txin_index].to_hex()
        script_len = len(spk) // 2
        preimage += bytes([script_len]) + h_to_b(spk)
        preimage += txin.sequence
    else:
        preimage += struct.pack("<I", txin_index)

    # --- SIGHASH_SINGLE: sha of this output ---
    if sighash_single:
        txout = tx.outputs[txin_index]
        amount_bytes = struct.pack("<Q", txout.amount)
        script_bytes = txout.script_pubkey.to_bytes()
        blob = amount_bytes + struct.pack("B", len(script_bytes)) + script_bytes
        preimage += hashlib.sha256(blob).digest()

    # --- Script-path extension (BIP 342) ---
    if ext_flag == 1:
        if script is None:
            raise ValueError("script is required for ext_flag=1 (script path)")
        leaf_hash = tagged_hash(
            bytes([leaf_ver]) + prepend_compact_size(script.to_bytes()),
            "TapLeaf",
        )
        preimage += leaf_hash
        preimage += bytes([0])  # key_version = 0
        preimage += b"\xff\xff\xff\xff"  # codesep_pos = 0xFFFFFFFF

    return preimage


def compute_sigmsg_digest(
    tx: Transaction,
    txin_index: int,
    script_pubkeys: Sequence[Script],
    amounts: Sequence[int],
    **kwargs,
) -> bytes:
    """
    Compute the 32-byte TapSighash digest from the raw preimage.

    Equivalent to ``get_transaction_taproot_digest`` but built from
    :func:`compute_sigmsg_preimage` for consistency checking.
    """
    preimage = compute_sigmsg_preimage(tx, txin_index, script_pubkeys, amounts, **kwargs)
    return tagged_hash(preimage, "TapSighash")
