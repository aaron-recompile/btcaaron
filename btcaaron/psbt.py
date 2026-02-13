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
