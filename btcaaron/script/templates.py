"""
btcaaron.script.templates - Reusable script templates
"""

import json
import hashlib
import struct
from typing import Any, Mapping, Optional, Sequence, Tuple, Union

from ..bip118 import apo_pubkey_bytes
from ..key import Key
from .script import RawScript, Script


def _to_payload_bytes(payload: Union[str, bytes, Mapping[str, Any]]) -> bytes:
    """Normalize payload into bytes for script data pushes."""
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    if isinstance(payload, Mapping):
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    raise ValueError("payload must be str, bytes, or mapping")


def _to_xonly_hex(signer: Union[Key, str]) -> str:
    """Accept Key or x-only pubkey hex string."""
    if isinstance(signer, Key):
        return signer.xonly
    if isinstance(signer, str):
        return signer
    raise ValueError("signer must be Key or x-only pubkey hex string")


def _to_32byte_hex(value: Union[bytes, str], *, field_name: str) -> str:
    """Normalize a 32-byte value into lowercase hex."""
    if isinstance(value, bytes):
        if len(value) != 32:
            raise ValueError(f"{field_name} must be 32 bytes")
        return value.hex()
    if isinstance(value, str):
        v = value.lower().strip()
        if v.startswith("0x"):
            v = v[2:]
        if len(v) != 64:
            raise ValueError(f"{field_name} must be 32 bytes (64 hex chars)")
        int(v, 16)  # validates hex
        return v
    raise ValueError(f"{field_name} must be bytes or hex string")


def _push_bytes_hex(data_hex: str) -> str:
    """Encode pushdata for small script templates (PUSHDATA opcodes)."""
    n = len(data_hex) // 2
    if n <= 75:
        return f"{n:02x}{data_hex}"
    if n <= 0xFF:
        return f"4c{n:02x}{data_hex}"
    if n <= 0xFFFF:
        return f"4d{n.to_bytes(2, 'little').hex()}{data_hex}"
    return f"4e{n.to_bytes(4, 'little').hex()}{data_hex}"


def _to_bytes(value: Union[bytes, str], *, field_name: str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        v = value.lower().strip()
        if v.startswith("0x"):
            v = v[2:]
        if len(v) % 2 != 0:
            raise ValueError(f"{field_name} hex must have even length")
        return bytes.fromhex(v)
    raise ValueError(f"{field_name} must be bytes or hex string")


def _ser_compact_size(n: int) -> bytes:
    if n < 253:
        return struct.pack("B", n)
    if n < 0x10000:
        return struct.pack("<BH", 253, n)
    if n < 0x100000000:
        return struct.pack("<BI", 254, n)
    return struct.pack("<BQ", 255, n)


def _ser_string(s: bytes) -> bytes:
    return _ser_compact_size(len(s)) + s


def _ser_txout(n_value: int, script_pubkey: bytes) -> bytes:
    return struct.pack("<q", n_value) + _ser_string(script_pubkey)


def ord_inscription_script(
    signer: Union[Key, str],
    payload: Union[str, bytes, Mapping[str, Any]],
    *,
    content_type: str = "text/plain;charset=utf-8",
    protocol: str = "ord",
) -> Script:
    """
    Build an Ordinals-style inscription envelope tapscript.

    Script shape:
        <xonly> OP_CHECKSIG OP_0 OP_IF
        <protocol> OP_1 <content_type> OP_0 <payload> OP_ENDIF
    """
    xonly = _to_xonly_hex(signer)
    payload_hex = _to_payload_bytes(payload).hex()
    protocol_hex = protocol.encode("utf-8").hex()
    content_type_hex = content_type.encode("utf-8").hex()

    return Script.from_ops([
        xonly,
        "OP_CHECKSIG",
        "OP_0",
        "OP_IF",
        protocol_hex,
        "OP_1",
        content_type_hex,
        "OP_0",
        payload_hex,
        "OP_ENDIF",
    ])


def brc20_mint_json(tick: str, amt: Union[str, int]) -> str:
    """Build canonical BRC-20 mint JSON payload."""
    payload = {
        "p": "brc-20",
        "op": "mint",
        "tick": str(tick),
        "amt": str(amt),
    }
    return json.dumps(payload, separators=(",", ":"))


def inq_cat_hashlock_script(expected_hash: Union[bytes, str]) -> RawScript:
    """
    Build Inquisition OP_CAT hashlock leaf script.

    Script:
        OP_CAT OP_SHA256 <32-byte-expected-hash> OP_EQUAL
    Witness convention:
        [part_a, part_b]
    """
    expected_hash_hex = _to_32byte_hex(expected_hash, field_name="expected_hash")
    script_hex = "7e" + "a8" + _push_bytes_hex(expected_hash_hex) + "87"
    return RawScript(script_hex)


def inq_csfs_script() -> RawScript:
    """
    Build Inquisition OP_CHECKSIGFROMSTACK leaf script.

    Script:
        OP_CHECKSIGFROMSTACK
    Witness convention:
        [signature, message32, pubkey32]
    """
    return RawScript("cc")


def inq_ctv_script(template_hash: Union[bytes, str]) -> RawScript:
    """
    Build Inquisition OP_CHECKTEMPLATEVERIFY leaf script.

    Script:
        <32-byte-template-hash> OP_CHECKTEMPLATEVERIFY
    """
    template_hash_hex = _to_32byte_hex(template_hash, field_name="template_hash")
    script_hex = _push_bytes_hex(template_hash_hex) + "b3"
    return RawScript(script_hex)


def inq_ctv_template_hash_for_outputs(
    outputs: Sequence[Tuple[int, Union[bytes, str]]],
    *,
    n_version: int = 2,
    n_locktime: int = 0,
    n_vin: int = 1,
    sequence: int = 0xFFFFFFFF,
    n_in: int = 0,
) -> bytes:
    """
    Compute CTV (BIP119-style) template hash for a multi-output template.

    ``outputs`` order must match the spend transaction's output order exactly.
    Each tuple is ``(value_sats, script_pubkey)`` with ``script_pubkey`` as hex or bytes.

    Same preimage layout as ``inq_ctv_template_hash_for_output`` for the single-output case.
    """
    if not outputs:
        raise ValueError("outputs must be non-empty")
    blob = b""
    for output_sats, spk in outputs:
        if output_sats < 0:
            raise ValueError("output_sats must be >= 0")
        script_pubkey = _to_bytes(spk, field_name="output_script_pubkey")
        blob += _ser_txout(output_sats, script_pubkey)
    sequences = struct.pack("<I", sequence)
    precomputed_sequences = hashlib.sha256(sequences).digest()
    precomputed_outputs = hashlib.sha256(blob).digest()
    n_vout = len(outputs)

    r = b""
    r += struct.pack("<i", n_version)
    r += struct.pack("<I", n_locktime)
    r += struct.pack("<I", n_vin)
    r += precomputed_sequences
    r += struct.pack("<I", n_vout)
    r += precomputed_outputs
    r += struct.pack("<I", n_in)
    return hashlib.sha256(r).digest()


def inq_ctv_template_hash_for_output(
    output_sats: int,
    output_script_pubkey: Union[bytes, str],
    *,
    n_version: int = 2,
    n_locktime: int = 0,
    n_vin: int = 1,
    sequence: int = 0xFFFFFFFF,
    n_vout: int = 1,
    n_in: int = 0,
) -> bytes:
    """
    Compute CTV template hash for a single-output template.

    This is the common Inquisition experiment pattern:
    one input, one output, fixed sequence.
    """
    if n_vout != 1:
        raise ValueError("use inq_ctv_template_hash_for_outputs for n_vout != 1")
    return inq_ctv_template_hash_for_outputs(
        [(output_sats, output_script_pubkey)],
        n_version=n_version,
        n_locktime=n_locktime,
        n_vin=n_vin,
        sequence=sequence,
        n_in=n_in,
    )


def inq_ctv_program_for_output(
    internal_key: Key,
    output_sats: int,
    output_script_pubkey: Union[bytes, str],
    *,
    network: str = "signet",
    label: str = "ctv",
    sequence: int = 0xFFFFFFFF,
):
    """
    Build a TapTree program that commits to a single-output CTV template.

    Returns:
        tuple(TaprootProgram, template_hash_bytes)
    """
    from ..tree import TapTree

    template_hash = inq_ctv_template_hash_for_output(
        output_sats=output_sats,
        output_script_pubkey=output_script_pubkey,
        sequence=sequence,
    )
    leaf_script = inq_ctv_script(template_hash)
    program = TapTree(internal_key=internal_key, network=network).custom(
        script=leaf_script,
        label=label,
    ).build()
    return program, template_hash


def inq_ctv_program_for_outputs(
    internal_key: Key,
    outputs: Sequence[Tuple[int, Union[bytes, str]]],
    *,
    network: str = "signet",
    label: str = "ctv",
    sequence: int = 0xFFFFFFFF,
):
    """
    TapTree with one CTV leaf committing to a **multi-output** template (UHPO-style splits).

    Spend with ``program.spend(label).from_utxo(...).to(a0,s0).to(a1,s1)...`` in the **same
    order** as ``outputs``.

    Returns:
        tuple(TaprootProgram, template_hash_bytes)
    """
    from ..tree import TapTree

    template_hash = inq_ctv_template_hash_for_outputs(
        list(outputs),
        sequence=sequence,
    )
    leaf_script = inq_ctv_script(template_hash)
    program = TapTree(internal_key=internal_key, network=network).custom(
        script=leaf_script,
        label=label,
    ).build()
    return program, template_hash


def inq_apo_checksig_script(signer: Union[Key, str]) -> RawScript:
    """
    BIP118 tapscript leaf for ``SIGHASH_ANYPREVOUT`` script-path spends.

    Script shape (see BIP118):
        <33-byte BIP118 pubkey> OP_CHECKSIG
    where the pubkey is ``0x01 || 32-byte x-only`` (not plain BIP340 x-only).

    Unlock with ``SpendBuilder.sign(key)`` on a program built via
    ``TapTree.bip118_checksig(...)`` or ``inq_apo_program(...)`` — signing uses
    ``Key.sign_taproot_script_bip118`` (sighash byte e.g. ``0x41``).

    **Consensus** requires a node that implements BIP118 (e.g. Bitcoin Inquisition).
    """
    xonly_hex = _to_xonly_hex(signer)
    apo_push = apo_pubkey_bytes(bytes.fromhex(xonly_hex))
    script_hex = _push_bytes_hex(apo_push.hex()) + "ac"
    return RawScript(script_hex)


def inq_apo_program(
    apo_signer: Key,
    *,
    internal_key: Optional[Key] = None,
    network: str = "signet",
    label: str = "apo",
):
    """
    Single-leaf Taproot program: BIP118 ``<0x01||xonly> OP_CHECKSIG``.

    ``apo_signer`` is the key that must sign the script-path spend (BIP118 sighash).

    If ``internal_key`` is omitted, it defaults to ``apo_signer`` (simplest demo:
    key-path and script-path share the same internal key).

    Returns:
        TaprootProgram
    """
    from ..tree import TapTree

    ik = internal_key if internal_key is not None else apo_signer
    return (
        TapTree(internal_key=ik, network=network)
        .bip118_checksig(apo_signer, label=label)
        .build()
    )
