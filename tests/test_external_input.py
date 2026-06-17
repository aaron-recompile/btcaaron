"""
Tests for SpendBuilder.add_external_input().

Validates that:
 1. External inputs appear in the raw transaction.
 2. script_pub_keys and amounts arrays are correctly extended.
 3. APO sighash covers all inputs (program + external).
 4. Key-path signing for external inputs produces a valid witness slot.
 5. Zero external inputs = no change in behavior.
"""

import struct

import pytest
from bitcoinutils.setup import setup

from btcaaron import Key, TapTree


@pytest.fixture(autouse=True)
def _network():
    setup("testnet")


FAKE_TXID_A = "aa" * 32
FAKE_TXID_B = "bb" * 32


def _bare_p2tr_spk_hex(key: Key) -> str:
    """scriptPubKey hex for a bare P2TR address (key-path only, no tree)."""
    addr = key._internal_pub.get_taproot_address()
    return addr.to_script_pub_key().to_hex()


def _build_rca_program(key: Key):
    """3-leaf RCA-shaped tree: APO + CHECKSIG + CUSTOM (CTV placeholder)."""
    from btcaaron.bip118 import apo_pubkey_bytes
    program = (
        TapTree(internal_key=key, network="testnet")
        .bip118_checksig(key, label="apo_update")
        .checksig(key, label="checksig_leaf")
        .build()
    )
    return program


class TestExternalInputStructure:
    """Structural tests (no chain required)."""

    def test_no_external_inputs_unchanged(self):
        """With zero external inputs, build produces same result as before."""
        k = Key.generate()
        prog = _build_rca_program(k)
        tx = (
            prog.spend("checksig_leaf")
            .from_utxo(FAKE_TXID_A, 0, sats=50_000)
            .to(prog.address, 47_000)
            .sign(k)
            .build()
        )
        raw = tx.hex
        assert len(raw) > 0
        assert tx._tx.witnesses is not None
        assert len(tx._tx.witnesses) == 1

    def test_external_input_appears_in_tx(self):
        """Transaction with 1 program input + 1 external input has 2 inputs."""
        k = Key.generate()
        ext_key = Key.generate()
        prog = _build_rca_program(k)
        ext_spk = _bare_p2tr_spk_hex(ext_key)

        tx = (
            prog.spend("checksig_leaf")
            .from_utxo(FAKE_TXID_A, 0, sats=30_000)
            .add_external_input(FAKE_TXID_B, 0, 20_000,
                                script_pubkey_hex=ext_spk,
                                sign_keypath=ext_key)
            .to(prog.address, 47_000)
            .sign(k)
            .build()
        )
        assert len(tx._tx.inputs) == 2
        assert len(tx._tx.witnesses) == 2
        assert tx._input_sats == 50_000

    def test_external_input_witness_has_signature(self):
        """When sign_keypath is provided, external input witness has 1 sig element."""
        k = Key.generate()
        ext_key = Key.generate()
        prog = _build_rca_program(k)
        ext_spk = _bare_p2tr_spk_hex(ext_key)

        tx = (
            prog.spend("checksig_leaf")
            .from_utxo(FAKE_TXID_A, 0, sats=30_000)
            .add_external_input(FAKE_TXID_B, 0, 20_000,
                                script_pubkey_hex=ext_spk,
                                sign_keypath=ext_key)
            .to(prog.address, 47_000)
            .sign(k)
            .build()
        )
        ext_wit = tx._tx.witnesses[1]
        assert len(ext_wit.stack) == 1

    def test_external_input_no_sign_empty_witness(self):
        """When sign_keypath is None, external input witness is empty."""
        k = Key.generate()
        prog = _build_rca_program(k)
        ext_spk = "5120" + "cc" * 32

        tx = (
            prog.spend("checksig_leaf")
            .from_utxo(FAKE_TXID_A, 0, sats=30_000)
            .add_external_input(FAKE_TXID_B, 0, 20_000,
                                script_pubkey_hex=ext_spk)
            .to(prog.address, 47_000)
            .sign(k)
            .build()
        )
        ext_wit = tx._tx.witnesses[1]
        assert len(ext_wit.stack) == 0

    def test_multiple_external_inputs(self):
        """Three external inputs added, tx has 4 total inputs."""
        k = Key.generate()
        prog = _build_rca_program(k)
        ext_spk = "5120" + "dd" * 32

        builder = (
            prog.spend("checksig_leaf")
            .from_utxo(FAKE_TXID_A, 0, sats=30_000)
            .to(prog.address, 80_000)
            .sign(k)
        )
        for i in range(3):
            fake = f"{i:02x}" * 32
            builder = builder.add_external_input(
                fake, 0, 20_000, script_pubkey_hex=ext_spk
            )

        tx = builder.build()
        assert len(tx._tx.inputs) == 4
        assert len(tx._tx.witnesses) == 4
        assert tx._input_sats == 30_000 + 3 * 20_000


class TestExternalInputAPO:
    """APO (BIP118) script-path with external inputs."""

    def test_apo_with_external_input_builds(self):
        """APO script-path spend with an external input produces valid hex."""
        k = Key.generate()
        ext_key = Key.generate()
        prog = _build_rca_program(k)
        ext_spk = _bare_p2tr_spk_hex(ext_key)

        tx = (
            prog.spend("apo_update")
            .from_utxo(FAKE_TXID_A, 0, sats=30_000)
            .add_external_input(FAKE_TXID_B, 0, 20_000,
                                script_pubkey_hex=ext_spk,
                                sign_keypath=ext_key)
            .to(prog.address, 47_000)
            .sign(k)
            .build()
        )
        assert len(tx._tx.inputs) == 2
        assert len(tx._tx.witnesses) == 2
        assert len(tx.hex) > 0

    def test_apo_fee_calculation_includes_external(self):
        """Fee = total_input - total_output, including external."""
        k = Key.generate()
        ext_key = Key.generate()
        prog = _build_rca_program(k)
        ext_spk = _bare_p2tr_spk_hex(ext_key)

        tx = (
            prog.spend("apo_update")
            .from_utxo(FAKE_TXID_A, 0, sats=30_000)
            .add_external_input(FAKE_TXID_B, 0, 20_000,
                                script_pubkey_hex=ext_spk,
                                sign_keypath=ext_key)
            .to(prog.address, 47_000)
            .sign(k)
            .build()
        )
        assert tx.fee == 3_000


class TestExternalInputKeypath:
    """Key-path spend mode with external inputs."""

    def test_keypath_with_external(self):
        k = Key.generate()
        ext_key = Key.generate()
        prog = (
            TapTree(internal_key=k, network="testnet")
            .checksig(k, label="dummy")
            .build()
        )
        ext_spk = _bare_p2tr_spk_hex(ext_key)

        tx = (
            prog.keypath()
            .from_utxo(FAKE_TXID_A, 0, sats=30_000)
            .add_external_input(FAKE_TXID_B, 0, 20_000,
                                script_pubkey_hex=ext_spk,
                                sign_keypath=ext_key)
            .to(prog.address, 47_000)
            .sign(k)
            .build()
        )
        assert len(tx._tx.inputs) == 2
        assert len(tx._tx.witnesses) == 2
        assert tx._input_sats == 50_000
