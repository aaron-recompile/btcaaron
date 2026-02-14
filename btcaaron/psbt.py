"""
btcaaron.psbt - Partially Signed Bitcoin Transaction (BIP 174 + BIP 371 Taproot)

PSBT v0 for Taproot: create, sign, finalize, extract.
Compatible with hardware wallets and other BIP 174 implementations.
"""

import base64
import struct
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .key import Key

# BIP 174 key types
PSBT_GLOBAL_UNSIGNED_TX = 0x00
PSBT_IN_WITNESS_UTXO = 0x01
PSBT_IN_FINAL_SCRIPTWITNESS = 0x08
# BIP 371 Taproot
PSBT_IN_TAP_KEY_SIG = 0x13
PSBT_IN_TAP_SCRIPT_SIG = 0x14
PSBT_IN_TAP_LEAF_SCRIPT = 0x15
PSBT_IN_TAP_INTERNAL_KEY = 0x17
PSBT_IN_TAP_MERKLE_ROOT = 0x18

PSBT_MAGIC = b"psbt\xff"


def _encode_varint(n: int) -> bytes:
    """Compact size encoding (BIP 174)."""
    if n < 0xfd:
        return struct.pack("B", n)
    elif n <= 0xffff:
        return b"\xfd" + struct.pack("<H", n)
    elif n <= 0xffffffff:
        return b"\xfe" + struct.pack("<I", n)
    else:
        return b"\xff" + struct.pack("<Q", n)


def _tapscript_pubkey_order(script_bytes: bytes) -> List[bytes]:
    """Extract 32-byte pubkeys from tapscript in appearance order (for MULTISIG witness ordering)."""
    order: List[bytes] = []
    i = 0
    while i < len(script_bytes):
        if script_bytes[i] == 0x20 and i + 33 <= len(script_bytes):  # OP_PUSH32
            order.append(script_bytes[i + 1 : i + 33])
            i += 33
        elif script_bytes[i] <= 0x4b:  # OP_1-OP_PUSHBYTES_75
            i += 1 + script_bytes[i]
        elif script_bytes[i] == 0x4c:  # OP_PUSHDATA1
            if i + 2 <= len(script_bytes):
                n = script_bytes[i + 1]
                if n == 32 and i + 34 <= len(script_bytes):
                    order.append(script_bytes[i + 2 : i + 34])
                i += 2 + n
            else:
                i += 1
        elif script_bytes[i] == 0x4d:  # OP_PUSHDATA2
            if i + 3 <= len(script_bytes):
                n = struct.unpack_from("<H", script_bytes, i + 1)[0]
                if n == 32 and i + 35 <= len(script_bytes):
                    order.append(script_bytes[i + 3 : i + 35])
                i += 3 + n
            else:
                i += 1
        else:
            i += 1
    return order


def _decode_varint(data: bytes, offset: int) -> Tuple[int, int]:
    """Decode compact size, return (value, bytes_consumed)."""
    if offset >= len(data):
        return 0, 0
    b = data[offset]
    if b < 0xfd:
        return b, 1
    elif b == 0xfd:
        return struct.unpack_from("<H", data, offset + 1)[0], 3
    elif b == 0xfe:
        return struct.unpack_from("<I", data, offset + 1)[0], 5
    else:
        return struct.unpack_from("<Q", data, offset + 1)[0], 9


def _read_key_value(data: bytes, offset: int) -> Tuple[Optional[Tuple[bytes, bytes]], int]:
    """Read one key-value pair. Returns ((key, value), new_offset) or (None, new_offset) on separator."""
    if offset >= len(data):
        return None, offset
    key_len, n = _decode_varint(data, offset)
    offset += n
    if key_len == 0:
        return None, offset
    key = data[offset : offset + key_len]
    offset += key_len
    val_len, n = _decode_varint(data, offset)
    offset += n
    value = data[offset : offset + val_len]
    offset += val_len
    return (key, value), offset


class PsbtInput:
    """Per-input PSBT data (Taproot)."""

    def __init__(self):
        self.witness_utxo: Optional[Tuple[int, bytes]] = None  # (amount, script_pubkey)
        self.tap_internal_key: Optional[bytes] = None
        self.tap_merkle_root: Optional[bytes] = None  # BIP 371: 32 bytes (empty = key-path no tree)
        self.tap_leaf_script: Optional[Tuple[bytes, bytes]] = None  # (script_bytes, control_block_bytes)
        self.tap_key_sig: Optional[bytes] = None
        self.tap_script_sigs: Dict[Tuple[bytes, bytes], bytes] = {}  # (xonly_pubkey, leaf_hash): sig
        self.final_script_witness: Optional[List[bytes]] = None
        # For signing: store script object when from SpendBuilder (avoids re-parse)
        self._tapleaf_script_obj = None


class Psbt:
    """
    Partially Signed Bitcoin Transaction (BIP 174 + BIP 371 Taproot).

    Example:
        psbt = (program.spend("2of2").from_utxo(...).to(...)).to_psbt()
        psbt.sign_with(alice_key, 0)
        psbt.sign_with(bob_key, 0)
        psbt.finalize()
        tx = psbt.extract_transaction()
    """

    def __init__(self, tx):
        self.tx = tx
        self.inputs: List[PsbtInput] = [PsbtInput() for _ in tx.inputs]

    @classmethod
    def from_base64(cls, b64: str) -> "Psbt":
        """Decode PSBT from base64 string."""
        raw = base64.b64decode(b64)
        if not raw.startswith(PSBT_MAGIC):
            raise ValueError("Invalid PSBT: bad magic")
        offset = len(PSBT_MAGIC)

        unsigned_tx_bytes = None
        while offset < len(raw):
            kv, offset = _read_key_value(raw, offset)
            if kv is None:
                break
            key, value = kv
            if len(key) == 1 and key[0] == PSBT_GLOBAL_UNSIGNED_TX:
                unsigned_tx_bytes = value
                # Don't break: continue to consume the map separator (0x00)

        if unsigned_tx_bytes is None:
            raise ValueError("Invalid PSBT: missing unsigned tx")

        from bitcoinutils.transactions import Transaction
        tx = Transaction.from_raw(unsigned_tx_bytes.hex())
        psbt = cls(tx)

        # Input maps (one per input)
        for i in range(len(tx.inputs)):
            while offset < len(raw):
                kv, offset = _read_key_value(raw, offset)
                if kv is None:
                    break
                key, value = kv
                if len(key) == 1:
                    kt = key[0]
                    if kt == PSBT_IN_WITNESS_UTXO:
                        amt = struct.unpack_from("<q", value, 0)[0]
                        script_len, n = _decode_varint(value, 8)
                        spk = value[8 + n : 8 + n + script_len]
                        psbt.inputs[i].witness_utxo = (amt, spk)
                    elif kt == PSBT_IN_TAP_INTERNAL_KEY:
                        psbt.inputs[i].tap_internal_key = value[:32]
                    elif kt == PSBT_IN_TAP_MERKLE_ROOT:
                        psbt.inputs[i].tap_merkle_root = value[:32]
                    elif kt == PSBT_IN_TAP_KEY_SIG:
                        psbt.inputs[i].tap_key_sig = value
                    elif kt == PSBT_IN_FINAL_SCRIPTWITNESS:
                        stack = []
                        off = 0
                        n_items, nn = _decode_varint(value, off)
                        off += nn
                        for _ in range(n_items):
                            item_len, nn = _decode_varint(value, off)
                            off += nn
                            stack.append(value[off : off + item_len])
                            off += item_len
                        psbt.inputs[i].final_script_witness = stack
                elif len(key) >= 33 and key[0] == PSBT_IN_TAP_LEAF_SCRIPT:
                    cb = key[1:]
                    leaf_ver = value[0]
                    script_len, n = _decode_varint(value, 1)
                    script = value[1 + n : 1 + n + script_len]
                    psbt.inputs[i].tap_leaf_script = (script, cb)
                elif len(key) == 65 and key[0] == PSBT_IN_TAP_SCRIPT_SIG:
                    pk, lh = key[1:33], key[33:65]
                    psbt.inputs[i].tap_script_sigs[(pk, lh)] = value

        return psbt

    def to_base64(self) -> str:
        """Encode PSBT to base64."""
        parts = [PSBT_MAGIC]
        unsigned = self.tx.to_bytes(False)
        parts.append(_encode_varint(1) + bytes([PSBT_GLOBAL_UNSIGNED_TX]) + _encode_varint(len(unsigned)) + unsigned)
        parts.append(b"\x00")

        for inp in self.inputs:
            if inp.witness_utxo:
                amt, spk = inp.witness_utxo
                val = struct.pack("<q", amt) + _encode_varint(len(spk)) + spk
                parts.append(_encode_varint(1) + bytes([PSBT_IN_WITNESS_UTXO]) + _encode_varint(len(val)) + val)
            if inp.tap_internal_key:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_TAP_INTERNAL_KEY]) + _encode_varint(32) + inp.tap_internal_key)
            if inp.tap_merkle_root is not None and len(inp.tap_merkle_root) == 32:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_TAP_MERKLE_ROOT]) + _encode_varint(32) + inp.tap_merkle_root)
            if inp.tap_leaf_script:
                script, cb = inp.tap_leaf_script
                key = bytes([PSBT_IN_TAP_LEAF_SCRIPT]) + cb
                val = bytes([0xC0]) + _encode_varint(len(script)) + script
                parts.append(_encode_varint(len(key)) + key + _encode_varint(len(val)) + val)
            if inp.tap_key_sig:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_TAP_KEY_SIG]) + _encode_varint(len(inp.tap_key_sig)) + inp.tap_key_sig)
            for (pk, lh), sig in inp.tap_script_sigs.items():
                key = bytes([PSBT_IN_TAP_SCRIPT_SIG]) + pk + lh
                parts.append(_encode_varint(len(key)) + key + _encode_varint(len(sig)) + sig)
            if inp.final_script_witness:
                val = _encode_varint(len(inp.final_script_witness))
                for item in inp.final_script_witness:
                    val += _encode_varint(len(item)) + item
                parts.append(_encode_varint(1) + bytes([PSBT_IN_FINAL_SCRIPTWITNESS]) + _encode_varint(len(val)) + val)
            parts.append(b"\x00")

        parts.append(b"\x00")
        return base64.b64encode(b"".join(parts)).decode("ascii")

    def sign_with(self, key: "Key", input_index: int = 0) -> None:
        """Add Taproot signature for input."""
        psbtin = self.inputs[input_index]
        if not psbtin.witness_utxo:
            raise ValueError(f"Missing witness UTXO for input {input_index}")

        script_pub_keys = []
        amounts = []
        for inp in self.inputs:
            amt, spk = inp.witness_utxo
            amounts.append(amt)
            try:
                from bitcoinutils.script import Script
                spk_obj = Script.from_raw(spk.hex(), has_segwit=True)
            except Exception:
                from bitcoinutils.script import Script
                spk_obj = Script([spk.hex()])  # fallback
            script_pub_keys.append(spk_obj)

        if psbtin.tap_leaf_script:
            script_bytes, _ = psbtin.tap_leaf_script
            if psbtin._tapleaf_script_obj is not None:
                tapleaf = psbtin._tapleaf_script_obj
            else:
                from bitcoinutils.script import Script
                tapleaf = Script.from_raw(script_bytes.hex(), has_segwit=True)
            sig = key._internal.sign_taproot_input(
                self.tx, input_index, script_pub_keys, amounts,
                script_path=True, tapleaf_script=tapleaf, tweak=False
            )
            from .tree import tapmath
            leaf_hash = tapmath.tapleaf_hash(script_bytes)
            pk = bytes.fromhex(key.xonly)
            sig_bytes = sig if isinstance(sig, bytes) else (bytes.fromhex(sig) if isinstance(sig, str) else sig)
            if hasattr(sig_bytes, '__iter__') and not isinstance(sig_bytes, (bytes, str)):
                sig_bytes = bytes(sig_bytes)
            psbtin.tap_script_sigs[(pk, leaf_hash)] = sig_bytes
        else:
            scripts_for_tweak = getattr(psbtin, '_tapleaf_scripts_for_tweak', None) or []
            sig = key._internal.sign_taproot_input(
                self.tx, input_index, script_pub_keys, amounts,
                script_path=False, tapleaf_scripts=scripts_for_tweak
            )
            sig_bytes = sig if isinstance(sig, bytes) else bytes.fromhex(sig)
            psbtin.tap_key_sig = sig_bytes

    def finalize(self) -> None:
        """Build final witnesses."""
        from bitcoinutils.transactions import TxWitnessInput

        # Ensure witness list length matches inputs
        while len(self.tx.witnesses) < len(self.tx.inputs):
            self.tx.witnesses.append(TxWitnessInput([]))

        for i, inp in enumerate(self.inputs):
            if inp.tap_key_sig:
                sig_hex = inp.tap_key_sig.hex() if isinstance(inp.tap_key_sig, bytes) else inp.tap_key_sig
                self.tx.witnesses[i] = TxWitnessInput([sig_hex])
            elif inp.tap_leaf_script and inp.tap_script_sigs:
                script_bytes, control_block = inp.tap_leaf_script
                from .tree import tapmath
                leaf_hash = tapmath.tapleaf_hash(script_bytes)
                sigs_by_pk = {}
                for (pk, lh), sig in inp.tap_script_sigs.items():
                    if lh == leaf_hash:
                        pk_bytes = pk if isinstance(pk, bytes) else bytes.fromhex(pk)
                        sigs_by_pk[pk_bytes] = sig.hex() if isinstance(sig, bytes) else sig
                # For MULTISIG: witness order = last pubkey's sig first (CHECKSIGADD LIFO)
                pubkey_order = _tapscript_pubkey_order(script_bytes)
                if pubkey_order:
                    sigs = [sigs_by_pk[pk] for pk in reversed(pubkey_order) if pk in sigs_by_pk]
                else:
                    sigs = list(sigs_by_pk.values())
                witness_stack = sigs + [script_bytes.hex(), control_block.hex()]
                inp.final_script_witness = [bytes.fromhex(x) if isinstance(x, str) else x for x in witness_stack]
                self.tx.witnesses[i] = TxWitnessInput([s.hex() if isinstance(s, bytes) else s for s in witness_stack])
            else:
                raise ValueError(f"Cannot finalize input {i}: missing signature")

    def extract_transaction(self):
        """Return the finalized transaction."""
        return self.tx

    def to_v2(self) -> "PsbtV2":
        """Convert v0 PSBT to v2 (BIP 370) format."""
        return PsbtV2.from_psbt_v0(self)


# ═══════════════════════════════════════════════════════════════════════════════
# PSBT v2 (BIP 370) - Skeleton
# ═══════════════════════════════════════════════════════════════════════════════
# v2 removes unsigned_tx from Global; tx fields live in per-input/output maps.
# BIP 371 Taproot fields unchanged. Enables incremental tx construction.
# ═══════════════════════════════════════════════════════════════════════════════

# BIP 370 Global key types
PSBT_GLOBAL_TX_VERSION = 0x02
PSBT_GLOBAL_FALLBACK_LOCKTIME = 0x03
PSBT_GLOBAL_INPUT_COUNT = 0x04
PSBT_GLOBAL_OUTPUT_COUNT = 0x05

# BIP 370 Input key types (transaction structure)
PSBT_IN_PREVIOUS_TXID = 0x0e
PSBT_IN_OUTPUT_INDEX = 0x0f
PSBT_IN_SEQUENCE = 0x10

# BIP 370 Output key types
PSBT_OUT_AMOUNT = 0x03
PSBT_OUT_SCRIPT = 0x04


class PsbtV2Input(PsbtInput):
    """Per-input PSBT v2 data: tx fields + BIP 371 Taproot."""

    def __init__(self):
        super().__init__()
        self.previous_txid: Optional[bytes] = None
        self.output_index: Optional[int] = None
        self.sequence: int = 0xFFFFFFFF


class PsbtV2Output:
    """Per-output PSBT v2 data."""

    def __init__(self):
        self.amount: int = 0
        self.script_pubkey: bytes = b""


class PsbtV2:
    """
    PSBT Version 2 (BIP 370) skeleton.

    Tx structure lives in per-input/output maps instead of global unsigned_tx.
    Enables incremental construction (add inputs/outputs after creation).
    BIP 371 Taproot fields unchanged.
    """

    def __init__(self):
        self.tx_version: int = 2
        self.fallback_locktime: int = 0
        self.inputs: List[PsbtV2Input] = []
        self.outputs: List[PsbtV2Output] = []

    @classmethod
    def from_psbt_v0(cls, psbt: Psbt) -> "PsbtV2":
        """Create PsbtV2 from a v0 Psbt."""
        v2 = cls()
        bu_tx = psbt.tx
        ver = getattr(bu_tx, "version", 2)
        v2.tx_version = struct.unpack("<I", ver)[0] if isinstance(ver, bytes) else int(ver)
        lock = getattr(bu_tx, "locktime", 0)
        v2.fallback_locktime = struct.unpack("<I", lock)[0] if isinstance(lock, bytes) else int(lock)
        for i, inp in enumerate(psbt.inputs):
            v2in = PsbtV2Input()
            v2in.witness_utxo = inp.witness_utxo
            v2in.tap_internal_key = inp.tap_internal_key
            v2in.tap_merkle_root = inp.tap_merkle_root
            v2in.tap_leaf_script = inp.tap_leaf_script
            v2in.tap_key_sig = inp.tap_key_sig
            v2in.tap_script_sigs = dict(inp.tap_script_sigs)
            v2in.final_script_witness = inp.final_script_witness
            v2in._tapleaf_script_obj = inp._tapleaf_script_obj
            bu_in = bu_tx.inputs[i]
            v2in.previous_txid = bytes.fromhex(bu_in.txid) if isinstance(bu_in.txid, str) else bu_in.txid
            v2in.output_index = bu_in.txout_index
            seq = bu_in.sequence
            v2in.sequence = struct.unpack("<I", seq)[0] if isinstance(seq, bytes) else seq
            v2.inputs.append(v2in)
        for out in bu_tx.outputs:
            v2out = PsbtV2Output()
            v2out.amount = out.amount
            spk = getattr(out, "script_pubkey", None) or getattr(out, "script_pub_key", None)
            v2out.script_pubkey = spk.to_bytes() if hasattr(spk, "to_bytes") else bytes.fromhex(spk.to_hex())
            v2.outputs.append(v2out)
        return v2

    @classmethod
    def from_base64(cls, b64: str) -> "PsbtV2":
        """Decode PSBT v2 from base64."""
        raw = base64.b64decode(b64)
        if not raw.startswith(PSBT_MAGIC):
            raise ValueError("Invalid PSBT: bad magic")
        offset = len(PSBT_MAGIC)
        v2 = cls()
        tx_version = fallback_locktime = input_count = output_count = None
        while offset < len(raw):
            kv, offset = _read_key_value(raw, offset)
            if kv is None:
                break
            key, value = kv
            if len(key) == 1:
                kt = key[0]
                if kt == PSBT_GLOBAL_TX_VERSION:
                    tx_version = struct.unpack("<I", value)[0]
                elif kt == PSBT_GLOBAL_FALLBACK_LOCKTIME:
                    fallback_locktime = struct.unpack("<I", value)[0]
                elif kt == PSBT_GLOBAL_INPUT_COUNT:
                    input_count, _ = _decode_varint(value, 0)
                elif kt == PSBT_GLOBAL_OUTPUT_COUNT:
                    output_count, _ = _decode_varint(value, 0)
        if tx_version is not None:
            v2.tx_version = tx_version
        if fallback_locktime is not None:
            v2.fallback_locktime = fallback_locktime
        if input_count is None or output_count is None:
            raise ValueError("Invalid PSBT v2: missing input/output count")
        for _ in range(input_count):
            inp = PsbtV2Input()
            while offset < len(raw):
                kv, offset = _read_key_value(raw, offset)
                if kv is None:
                    break
                key, value = kv
                if len(key) == 1:
                    kt = key[0]
                    if kt == PSBT_IN_PREVIOUS_TXID:
                        inp.previous_txid = value[:32]
                    elif kt == PSBT_IN_OUTPUT_INDEX:
                        inp.output_index = struct.unpack("<I", value)[0]
                    elif kt == PSBT_IN_SEQUENCE:
                        inp.sequence = struct.unpack("<I", value)[0]
                    elif kt == PSBT_IN_WITNESS_UTXO:
                        amt = struct.unpack_from("<q", value, 0)[0]
                        script_len, n = _decode_varint(value, 8)
                        spk = value[8 + n : 8 + n + script_len]
                        inp.witness_utxo = (amt, spk)
                    elif kt == PSBT_IN_TAP_INTERNAL_KEY:
                        inp.tap_internal_key = value[:32]
                    elif kt == PSBT_IN_TAP_MERKLE_ROOT:
                        inp.tap_merkle_root = value[:32]
                    elif kt == PSBT_IN_TAP_KEY_SIG:
                        inp.tap_key_sig = value
                    elif kt == PSBT_IN_FINAL_SCRIPTWITNESS:
                        stack = []
                        off = 0
                        n_items, nn = _decode_varint(value, off)
                        off += nn
                        for _ in range(n_items):
                            item_len, nn = _decode_varint(value, off)
                            off += nn
                            stack.append(value[off : off + item_len])
                            off += item_len
                        inp.final_script_witness = stack
                elif len(key) >= 33 and key[0] == PSBT_IN_TAP_LEAF_SCRIPT:
                    cb = key[1:]
                    script_len, n = _decode_varint(value, 1)
                    script = value[1 + n : 1 + n + script_len]
                    inp.tap_leaf_script = (script, cb)
                elif len(key) == 65 and key[0] == PSBT_IN_TAP_SCRIPT_SIG:
                    pk, lh = key[1:33], key[33:65]
                    inp.tap_script_sigs[(pk, lh)] = value
            v2.inputs.append(inp)
        for _ in range(output_count):
            out = PsbtV2Output()
            while offset < len(raw):
                kv, offset = _read_key_value(raw, offset)
                if kv is None:
                    break
                key, value = kv
                if len(key) == 1:
                    kt = key[0]
                    if kt == PSBT_OUT_AMOUNT:
                        out.amount = struct.unpack("<q", value)[0]
                    elif kt == PSBT_OUT_SCRIPT:
                        out.script_pubkey = value
            v2.outputs.append(out)
        return v2

    def to_base64(self) -> str:
        """Encode PSBT v2 to base64."""
        parts = [PSBT_MAGIC]
        parts.append(_encode_varint(1) + bytes([PSBT_GLOBAL_TX_VERSION]) + _encode_varint(4) + struct.pack("<I", int(self.tx_version or 2)))
        parts.append(_encode_varint(1) + bytes([PSBT_GLOBAL_FALLBACK_LOCKTIME]) + _encode_varint(4) + struct.pack("<I", int(self.fallback_locktime)))
        inp_count_enc = _encode_varint(len(self.inputs))
        out_count_enc = _encode_varint(len(self.outputs))
        parts.append(_encode_varint(1) + bytes([PSBT_GLOBAL_INPUT_COUNT]) + _encode_varint(len(inp_count_enc)) + inp_count_enc)
        parts.append(_encode_varint(1) + bytes([PSBT_GLOBAL_OUTPUT_COUNT]) + _encode_varint(len(out_count_enc)) + out_count_enc)
        parts.append(b"\x00")
        for inp in self.inputs:
            if inp.previous_txid:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_PREVIOUS_TXID]) + _encode_varint(32) + inp.previous_txid)
            if inp.output_index is not None:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_OUTPUT_INDEX]) + _encode_varint(4) + struct.pack("<I", inp.output_index))
            parts.append(_encode_varint(1) + bytes([PSBT_IN_SEQUENCE]) + _encode_varint(4) + struct.pack("<I", inp.sequence))
            if inp.witness_utxo:
                amt, spk = inp.witness_utxo
                val = struct.pack("<q", amt) + _encode_varint(len(spk)) + spk
                parts.append(_encode_varint(1) + bytes([PSBT_IN_WITNESS_UTXO]) + _encode_varint(len(val)) + val)
            if inp.tap_internal_key:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_TAP_INTERNAL_KEY]) + _encode_varint(32) + inp.tap_internal_key)
            if inp.tap_merkle_root is not None and len(inp.tap_merkle_root) == 32:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_TAP_MERKLE_ROOT]) + _encode_varint(32) + inp.tap_merkle_root)
            if inp.tap_leaf_script:
                script, cb = inp.tap_leaf_script
                key = bytes([PSBT_IN_TAP_LEAF_SCRIPT]) + cb
                val = bytes([0xC0]) + _encode_varint(len(script)) + script
                parts.append(_encode_varint(len(key)) + key + _encode_varint(len(val)) + val)
            if inp.tap_key_sig:
                parts.append(_encode_varint(1) + bytes([PSBT_IN_TAP_KEY_SIG]) + _encode_varint(len(inp.tap_key_sig)) + inp.tap_key_sig)
            for (pk, lh), sig in inp.tap_script_sigs.items():
                key = bytes([PSBT_IN_TAP_SCRIPT_SIG]) + pk + lh
                parts.append(_encode_varint(len(key)) + key + _encode_varint(len(sig)) + sig)
            if inp.final_script_witness:
                val = _encode_varint(len(inp.final_script_witness))
                for item in inp.final_script_witness:
                    val += _encode_varint(len(item)) + item
                parts.append(_encode_varint(1) + bytes([PSBT_IN_FINAL_SCRIPTWITNESS]) + _encode_varint(len(val)) + val)
            parts.append(b"\x00")
        for out in self.outputs:
            parts.append(_encode_varint(1) + bytes([PSBT_OUT_AMOUNT]) + _encode_varint(8) + struct.pack("<q", out.amount))
            parts.append(_encode_varint(1) + bytes([PSBT_OUT_SCRIPT]) + _encode_varint(len(out.script_pubkey)) + out.script_pubkey)
            parts.append(b"\x00")
        return base64.b64encode(b"".join(parts)).decode("ascii")

    def extract_transaction(self):
        """Assemble bitcoinutils Transaction from v2 maps."""
        from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
        from bitcoinutils.script import Script

        txins = []
        for inp in self.inputs:
            txid_hex = inp.previous_txid.hex() if inp.previous_txid else "0" * 64
            seq = inp.sequence if inp.sequence is not None else 0xFFFFFFFF
            seq_bytes = struct.pack("<I", seq)
            txin = TxInput(txid_hex, inp.output_index or 0, sequence=seq_bytes)
            txins.append(txin)
        txouts = []
        for out in self.outputs:
            try:
                spk = Script.from_raw(out.script_pubkey.hex(), has_segwit=True)
            except Exception:
                spk = Script([out.script_pubkey.hex()])
            txouts.append(TxOutput(out.amount, spk))
        tx = Transaction(txins, txouts, has_segwit=True)
        while len(tx.witnesses) < len(tx.inputs):
            tx.witnesses.append(TxWitnessInput([]))
        for i, inp in enumerate(self.inputs):
            if inp.final_script_witness:
                stack = [w.hex() if isinstance(w, bytes) else w for w in inp.final_script_witness]
                tx.witnesses[i] = TxWitnessInput(stack)
        return tx
