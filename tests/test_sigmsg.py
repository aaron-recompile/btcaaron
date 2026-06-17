"""
Tests for btcaaron.sigmsg — BIP 341 SigMsg raw preimage computation.

Verification strategy:
  1. Preimage LENGTH matches BIP 341 formula for every sighash combo.
  2. Digest from our preimage == bitcoinutils get_transaction_taproot_digest.
"""

import pytest

from bitcoinutils.constants import (
    SIGHASH_ALL,
    SIGHASH_ANYONECANPAY,
    SIGHASH_NONE,
    SIGHASH_SINGLE,
    TAPROOT_SIGHASH_ALL,
)
from bitcoinutils.script import Script
from bitcoinutils.setup import setup
from bitcoinutils.transactions import Transaction, TxInput, TxOutput

from btcaaron import Key
from btcaaron.sigmsg import compute_sigmsg_digest, compute_sigmsg_preimage


@pytest.fixture(autouse=True)
def _setup_network():
    setup("testnet")


def _build_simple_tx():
    """Build a minimal 1-in-1-out P2TR transaction for testing."""
    k = Key.generate("testnet")
    pub = k._internal.get_public_key()
    addr = pub.get_taproot_address()
    spk = Script(["OP_1", pub.to_x_only_hex()])

    txin = TxInput("aa" * 32, 0, sequence=b"\xfd\xff\xff\xff")
    txout = TxOutput(50_000, addr.to_script_pub_key())
    tx = Transaction([txin], [txout])
    return tx, [spk], [100_000]


def _build_2in_tx():
    """Build a 2-in-1-out P2TR transaction."""
    k = Key.generate("testnet")
    pub = k._internal.get_public_key()
    addr = pub.get_taproot_address()
    spk = Script(["OP_1", pub.to_x_only_hex()])

    txin0 = TxInput("aa" * 32, 0, sequence=b"\xfd\xff\xff\xff")
    txin1 = TxInput("bb" * 32, 1, sequence=b"\xfe\xff\xff\xff")
    txout = TxOutput(90_000, addr.to_script_pub_key())
    tx = Transaction([txin0, txin1], [txout])
    return tx, [spk, spk], [50_000, 60_000]


class TestPreimageLength:
    """Verify preimage length matches BIP 341 formula."""

    def _preimage_len(self, sighash, ext_flag=0, script=None):
        tx, spks, amts = _build_simple_tx()
        kwargs = dict(ext_flag=ext_flag, sighash=sighash)
        if script is not None:
            kwargs["script"] = script
        pre = compute_sigmsg_preimage(tx, 0, spks, amts, **kwargs)
        return len(pre)

    def test_sighash_all_keypath(self):
        # epoch(1) + hash_type(1) + version(4) + locktime(4)
        # + sha_prevouts(32) + sha_amounts(32) + sha_scriptpubkeys(32) + sha_sequences(32)
        # + sha_outputs(32) + spend_type(1) + input_index(4) = 175
        assert self._preimage_len(TAPROOT_SIGHASH_ALL) == 175

    def test_sighash_all_explicit_keypath(self):
        assert self._preimage_len(SIGHASH_ALL) == 175

    def test_sighash_none_keypath(self):
        # sha_outputs omitted → 175 - 32 = 143
        assert self._preimage_len(SIGHASH_NONE) == 143

    def test_sighash_single_keypath(self):
        # sha_outputs omitted but sha_single_output added → 175 - 32 + 32 = 175
        assert self._preimage_len(SIGHASH_SINGLE) == 175

    def test_sighash_anyonecanpay_all_keypath(self):
        # 4 sha fields(128) + input_index(4) replaced by
        # outpoint(36) + amount(8) + scriptpubkey(35) + sequence(4) = 83
        # net change: 132 → 83, diff = -49
        # 175 - 49 = 126
        assert self._preimage_len(SIGHASH_ALL | SIGHASH_ANYONECANPAY) == 126

    def test_sighash_anyonecanpay_none_keypath(self):
        # 126 - 32 (no sha_outputs) = 94
        assert self._preimage_len(SIGHASH_NONE | SIGHASH_ANYONECANPAY) == 94

    def test_sighash_all_scriptpath(self):
        # key-path 175 + tapleaf_hash(32) + key_version(1) + codesep_pos(4) = 212
        script = Script(["OP_1"])
        assert self._preimage_len(TAPROOT_SIGHASH_ALL, ext_flag=1, script=script) == 212

    def test_sighash_none_scriptpath(self):
        # 143 + 37 = 180
        script = Script(["OP_1"])
        assert self._preimage_len(SIGHASH_NONE, ext_flag=1, script=script) == 180


class TestDigestMatchesBitcoinutils:
    """Our digest must match bitcoinutils get_transaction_taproot_digest exactly."""

    @pytest.mark.parametrize("sighash", [
        TAPROOT_SIGHASH_ALL,
        SIGHASH_ALL,
        SIGHASH_NONE,
        SIGHASH_SINGLE,
        SIGHASH_ALL | SIGHASH_ANYONECANPAY,
        SIGHASH_NONE | SIGHASH_ANYONECANPAY,
        SIGHASH_SINGLE | SIGHASH_ANYONECANPAY,
    ])
    def test_keypath_digest_1in(self, sighash):
        tx, spks, amts = _build_simple_tx()
        our = compute_sigmsg_digest(tx, 0, spks, amts, sighash=sighash)
        ref = tx.get_transaction_taproot_digest(0, spks, amts, sighash=sighash)
        assert our == ref, f"sighash={sighash:#x}: our={our.hex()} ref={ref.hex()}"

    @pytest.mark.parametrize("sighash", [
        TAPROOT_SIGHASH_ALL,
        SIGHASH_NONE,
        SIGHASH_ALL | SIGHASH_ANYONECANPAY,
    ])
    def test_keypath_digest_2in(self, sighash):
        tx, spks, amts = _build_2in_tx()
        for idx in range(2):
            our = compute_sigmsg_digest(tx, idx, spks, amts, sighash=sighash)
            ref = tx.get_transaction_taproot_digest(idx, spks, amts, sighash=sighash)
            assert our == ref, f"idx={idx} sighash={sighash:#x}"

    @pytest.mark.parametrize("sighash", [
        TAPROOT_SIGHASH_ALL,
        SIGHASH_NONE,
    ])
    def test_scriptpath_digest(self, sighash):
        tx, spks, amts = _build_simple_tx()
        script = Script(["OP_1"])
        our = compute_sigmsg_digest(
            tx, 0, spks, amts, ext_flag=1, script=script, sighash=sighash,
        )
        ref = tx.get_transaction_taproot_digest(
            0, spks, amts, ext_flag=1, script=script, sighash=sighash,
        )
        assert our == ref


class TestPreimageProperties:
    """Sanity checks on the raw preimage."""

    def test_epoch_byte_is_zero(self):
        tx, spks, amts = _build_simple_tx()
        pre = compute_sigmsg_preimage(tx, 0, spks, amts)
        assert pre[0] == 0, "first byte must be epoch 0x00"

    def test_second_byte_is_sighash(self):
        tx, spks, amts = _build_simple_tx()
        for sh in [TAPROOT_SIGHASH_ALL, SIGHASH_NONE, SIGHASH_ALL | SIGHASH_ANYONECANPAY]:
            pre = compute_sigmsg_preimage(tx, 0, spks, amts, sighash=sh)
            assert pre[1] == sh, f"byte[1] should be sighash {sh:#x}, got {pre[1]:#x}"

    def test_different_sighash_different_preimage(self):
        tx, spks, amts = _build_simple_tx()
        pre_all = compute_sigmsg_preimage(tx, 0, spks, amts, sighash=SIGHASH_ALL)
        pre_none = compute_sigmsg_preimage(tx, 0, spks, amts, sighash=SIGHASH_NONE)
        assert pre_all != pre_none
        assert len(pre_all) != len(pre_none)

    def test_ext_flag_1_requires_script(self):
        tx, spks, amts = _build_simple_tx()
        with pytest.raises(ValueError, match="script is required"):
            compute_sigmsg_preimage(tx, 0, spks, amts, ext_flag=1)
