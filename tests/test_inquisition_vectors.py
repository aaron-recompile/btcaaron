"""
Cross-check btcaaron's BIP 446 template hash and BIP 118 signature message against
Bitcoin Inquisition's reference implementation.

Expected values in tests/vectors/inquisition_v29.4_vectors.json were produced by
tools/gen_inquisition_vectors.py with Bitcoin Inquisition v29.4-inq's Python test
framework (TemplateMsg, and TaprootSignatureMsg with KEY_VERSION_ANYPREVOUT) over
random transactions: 1-4 inputs and outputs, mixed script types, random version,
locktime and sequences, with and without an annex, and all six ANYPREVOUT hash types.
"""

import json
from pathlib import Path

import pytest

from bitcoinutils.setup import setup
from bitcoinutils.transactions import Transaction

from btcaaron.bip118 import bip118_sighash, ext118, msg118
from btcaaron.templatehash import template_hash, template_msg

VECTORS = json.loads(
    (Path(__file__).parent / "vectors" / "inquisition_v29.4_vectors.json").read_text()
)


@pytest.fixture(autouse=True)
def _setup_network():
    setup("testnet")  # vectors are network-independent; keep the suite-wide default


class _RawScript:
    """Exact script bytes; avoids re-encoding random scripts through bitcoinutils."""

    def __init__(self, hex_str: str):
        self._raw = bytes.fromhex(hex_str)

    def to_bytes(self) -> bytes:
        return self._raw

    def to_hex(self) -> str:
        return self._raw.hex()


def _annex(case):
    return bytes.fromhex(case["annex"]) if case["annex"] is not None else None


@pytest.mark.parametrize("case", VECTORS["template_hash"], ids=lambda c: c["expected_hash"][:12])
def test_template_hash_matches_inquisition(case):
    outputs = [(amt, bytes.fromhex(spk)) for amt, spk in case["outputs"]]
    args = (case["version"], case["locktime"], case["sequences"], outputs, case["input_index"], _annex(case))
    assert template_msg(*args).hex() == case["expected_msg"]
    assert template_hash(*args).hex() == case["expected_hash"]


@pytest.mark.parametrize(
    "case",
    VECTORS["bip118"],
    ids=lambda c: f"{c['hash_type']:#04x}-{c['expected_sighash'][:10]}",
)
def test_bip118_matches_inquisition(case):
    tx = Transaction.from_raw(case["tx_hex"])
    for txout, (_, spk) in zip(tx.outputs, case["outputs"]):
        txout.script_pubkey = _RawScript(spk)
    spks = [_RawScript(spk) for _, spk in case["spent"]]
    amounts = [amt for amt, _ in case["spent"]]
    leaf = _RawScript(case["leaf_script"])
    idx, hash_type, annex = case["input_index"], case["hash_type"], _annex(case)

    preimage = b"\x00" + msg118(tx, idx, spks, amounts, hash_type, annex=annex) + ext118(leaf, hash_type)
    assert preimage.hex() == case["expected_msg"]
    digest = bip118_sighash(tx, idx, spks, amounts, leaf, hash_type, annex=annex)
    assert digest.hex() == case["expected_sighash"]
