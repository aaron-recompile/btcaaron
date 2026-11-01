"""
BIP 341 official test vectors for btcaaron.sigmsg.

Source: bitcoin/bips, bip-0341/wallet-test-vectors.json (keyPathSpending), stored
unmodified in tests/vectors/. For every input in the vector transaction we rebuild the
SigMsg preimage and the TapSighash digest and compare them byte-for-byte with the
values published in the BIP. This covers SIGHASH_DEFAULT, ALL, NONE, SINGLE and their
ANYONECANPAY variants.
"""

import json
from pathlib import Path

import pytest

from bitcoinutils.script import Script
from bitcoinutils.setup import setup
from bitcoinutils.transactions import Transaction

from btcaaron.sigmsg import compute_sigmsg_digest, compute_sigmsg_preimage

VECTORS = json.loads(
    (Path(__file__).parent / "vectors" / "bip341_wallet_test_vectors.json").read_text()
)
KEYPATH = VECTORS["keyPathSpending"][0]


@pytest.fixture(autouse=True)
def _setup_network():
    setup("testnet")  # vectors are network-independent; keep the suite-wide default


class _RawScriptBytes:
    """Exact scriptPubKey bytes for sigmsg (which only calls to_bytes()/to_hex())."""

    def __init__(self, raw: bytes):
        self._raw = raw

    def to_bytes(self) -> bytes:
        return self._raw

    def to_hex(self) -> str:
        return self._raw.hex()


def _raw_output_scripts(raw_tx_hex: str):
    """Parse output scriptPubKeys straight from the serialized transaction.

    The vector deliberately includes a non-standard output script containing the
    undefined opcode 0xf5, which bitcoinutils' Script parser does not round-trip.
    Supplying the exact bytes keeps the test about btcaaron's SigMsg logic only.
    """
    raw = bytes.fromhex(raw_tx_hex)
    i = 4

    def varint():
        nonlocal i
        n = raw[i]
        i += 1
        if n < 0xFD:
            return n
        size = {0xFD: 2, 0xFE: 4, 0xFF: 8}[n]
        v = int.from_bytes(raw[i:i + size], "little")
        i += size
        return v

    for _ in range(varint()):
        i += 36
        script_len = varint()
        i += script_len + 4
    scripts = []
    for _ in range(varint()):
        i += 8
        n = varint()
        scripts.append(raw[i:i + n])
        i += n
    return scripts


def _vector_tx():
    raw_hex = KEYPATH["given"]["rawUnsignedTx"]
    tx = Transaction.from_raw(raw_hex)
    for txout, spk in zip(tx.outputs, _raw_output_scripts(raw_hex)):
        txout.script_pubkey = _RawScriptBytes(spk)
    return tx


def _spent():
    utxos = KEYPATH["given"]["utxosSpent"]
    spks = [Script.from_raw(u["scriptPubKey"]) for u in utxos]
    amounts = [u["amountSats"] for u in utxos]
    return spks, amounts


@pytest.mark.parametrize(
    "case",
    KEYPATH["inputSpending"],
    ids=lambda c: f"in{c['given']['txinIndex']}-hashtype{c['given']['hashType']:#04x}",
)
def test_keypath_sigmsg_matches_bip341(case):
    tx = _vector_tx()
    spks, amounts = _spent()
    idx = case["given"]["txinIndex"]
    hash_type = case["given"]["hashType"]

    preimage = compute_sigmsg_preimage(tx, idx, spks, amounts, sighash=hash_type)
    # The BIP's sigMsg includes the leading epoch byte (0x00).
    assert preimage.hex() == case["intermediary"]["sigMsg"]

    digest = compute_sigmsg_digest(tx, idx, spks, amounts, sighash=hash_type)
    assert digest.hex() == case["intermediary"]["sigHash"]
