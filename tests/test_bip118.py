"""
BIP118 sighash + Key.sign_taproot_script_bip118 tests.
"""

import struct

import pytest
from bitcoinutils.keys import P2trAddress
from bitcoinutils.script import Script
from bitcoinutils.setup import setup
from bitcoinutils.transactions import Transaction, TxInput, TxOutput

from btcaaron import Key
from btcaaron.bip118 import (
    SIGHASH_DEFAULT_APO,
    apo_digest_same_for_different_prevouts,
    apo_pubkey_bytes,
    bip118_sighash,
)


@pytest.fixture(autouse=True)
def _network():
    setup("testnet")


def _p2tr_spk(addr_str: str):
    return P2trAddress(addr_str).to_script_pub_key()


def _two_txs_differ_only_prevout(addr: str, amount_sats: int):
    """Same outputs, same input amount/spk; only input txid differs."""
    spk = _p2tr_spk(addr)
    out = TxOutput(amount_sats, spk)
    v = b"\x02\x00\x00\x00"
    lt = b"\x00\x00\x00\x00"
    seq = struct.pack("<I", 0xFFFFFFFD)

    def make_tx(txid_hex: str):
        tin = TxInput(txid_hex, 0)
        tin.sequence = seq
        return Transaction([tin], [out], has_segwit=True)

    a = make_tx("1111111111111111111111111111111111111111111111111111111111111111")
    b = make_tx("2222222222222222222222222222222222222222222222222222222222222222")
    return a, b


def test_apo_digest_invariant_different_prevouts():
    """ANYPREVOUT: digest must not depend on which outpoint is spent (same spk+value)."""
    k = Key.generate("testnet")
    addr = k._internal_pub.get_taproot_address().to_string()
    amt = 100_000
    tx_a, tx_b = _two_txs_differ_only_prevout(addr, amt)
    spk = _p2tr_spk(addr)
    xonly = bytes.fromhex(k.xonly)
    leaf = Script([apo_pubkey_bytes(xonly).hex(), "OP_CHECKSIG"])

    assert apo_digest_same_for_different_prevouts(
        tx_a, tx_b, 0, [spk], [amt], leaf, SIGHASH_DEFAULT_APO
    )


def test_bip118_sighash_deterministic():
    k = Key.generate("testnet")
    addr = k._internal_pub.get_taproot_address().to_string()
    amt = 50_000
    tx_a, _ = _two_txs_differ_only_prevout(addr, amt)
    spk = _p2tr_spk(addr)
    xonly = bytes.fromhex(k.xonly)
    leaf = Script([apo_pubkey_bytes(xonly).hex(), "OP_CHECKSIG"])
    d1 = bip118_sighash(tx_a, 0, [spk], [amt], leaf, SIGHASH_DEFAULT_APO)
    d2 = bip118_sighash(tx_a, 0, [spk], [amt], leaf, SIGHASH_DEFAULT_APO)
    assert d1 == d2
    assert len(d1) == 32


def test_sign_taproot_script_bip118_produces_65_byte_hex_sig():
    k = Key.generate("testnet")
    addr = k._internal_pub.get_taproot_address().to_string()
    amt = 50_000
    tx, _ = _two_txs_differ_only_prevout(addr, amt)
    spk = _p2tr_spk(addr)
    xonly = bytes.fromhex(k.xonly)
    leaf = Script([apo_pubkey_bytes(xonly).hex(), "OP_CHECKSIG"])

    sig_hex = k.sign_taproot_script_bip118(
        tx, 0, [spk], [amt], leaf, hash_type=SIGHASH_DEFAULT_APO
    )
    assert len(sig_hex) == 130  # 65 bytes
    assert sig_hex[-2:] == "41"  # sighash byte
