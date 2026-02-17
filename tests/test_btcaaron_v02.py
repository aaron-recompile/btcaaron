"""
btcaaron v0.2.0 Test Suite

This file contains both unit tests and integration tests with
real testnet transaction records for verification.

Run with: pytest tests/test_btcaaron_v0.2.py -v
"""

import pytest
from unittest.mock import patch
from btcaaron import Key, TapTree, Psbt, quick_transfer


# ============================================================================
# Test Keys (Testnet)
# ============================================================================

ALICE_WIF = "cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT"
BOB_WIF = "cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG"

# Expected values from Chapter 8
ALICE_XONLY = "50be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3"
BOB_XONLY = "84b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5"

# 4-leaf Taproot address
EXPECTED_ADDRESS = "tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q"


# ============================================================================
# Verified Testnet Transactions
# ============================================================================

VERIFIED_TXS = {
    "hashlock": {
        "txid": "d67cf29fc6cfef1490d39dc4753dc4a3cdac8e69ce7c5b39cfdea1c233dbeea5",
        "input_txid": "1ac1291483b44528e711af42b2c959b8b06fc467231f6c1f8fb365e9ca3372b3",
        "input_vout": 1,
        "input_sats": 3000,
        "output_sats": 2500,
        "fee": 500,
        "preimage": "helloworld",
        "url": "https://mempool.space/testnet/tx/d67cf29fc6cfef1490d39dc4753dc4a3cdac8e69ce7c5b39cfdea1c233dbeea5",
    },
    "multisig": {
        "txid": "93c0e6ab682e2e5d088cc8175aaddc5d62f4b1de2b234dad566085a97b60581d",
        "input_txid": "76906b969d65177c5d8af3103e683aa1c02abafa94368d6a6ae1fe78b8aa49dd",
        "input_vout": 0,
        "input_sats": 2888,
        "output_sats": 2388,
        "fee": 500,
        "signers": ["alice", "bob"],
        "url": "https://mempool.space/testnet/tx/93c0e6ab682e2e5d088cc8175aaddc5d62f4b1de2b234dad566085a97b60581d",
    },
    "checksig_bob": {
        "txid": "5307d45a0302226ec8938cf44b2e1ee768769ea04d0a34dcda5c15563c21ef13",
        "input_txid": "fa86d9af50f9e8ec77fcbc4e514f748529612337f7ba0a25e285557facbf433d",
        "input_vout": 1,
        "input_sats": 1888,
        "output_sats": 1388,
        "fee": 500,
        "signer": "bob",
        "url": "https://mempool.space/testnet/tx/5307d45a0302226ec8938cf44b2e1ee768769ea04d0a34dcda5c15563c21ef13",
    },
    "keypath": {
        "txid": "63f444792332bcb173975fa2cf4d88a2620bc47b9d434768bf23477667f963b4",
        "input_txid": "a1d7aaff7316fda7dd557632d992c6e57a4bfcf145192b9d618be36d4090638d",
        "input_vout": 0,
        "input_sats": 2686,
        "output_sats": 2186,
        "fee": 500,
        "signer": "alice (internal key)",
        "url": "https://mempool.space/testnet/tx/63f444792332bcb173975fa2cf4d88a2620bc47b9d434768bf23477667f963b4",
    },
    "csv_timelock": {
        "txid": "dc48b4b9122b59a92d96dda21796b598e1e1b45388c17b3fd42b7c01dba3a122",
        "input_txid": "3ff99c8eaf9b9e2f42016f2b4c7659e11c8dcb4dc36f24ed7288a63b04c308f0",
        "input_vout": 1,
        "input_sats": 2666,
        "output_sats": 2166,
        "fee": 500,
        "signer": "bob",
        "blocks": 2,
        "url": "https://mempool.space/testnet/tx/dc48b4b9122b59a92d96dda21796b598e1e1b45388c17b3fd42b7c01dba3a122",
    },
}


# ============================================================================
# Unit Tests - Key
# ============================================================================

class TestKey:
    """Test Key class functionality"""
    
    def test_from_wif_alice(self):
        """Alice key derivation"""
        alice = Key.from_wif(ALICE_WIF)
        assert alice.xonly == ALICE_XONLY
    
    def test_from_wif_bob(self):
        """Bob key derivation"""
        bob = Key.from_wif(BOB_WIF)
        assert bob.xonly == BOB_XONLY
    
    def test_invalid_wif(self):
        """Invalid WIF should raise ValueError"""
        with pytest.raises(ValueError):
            Key.from_wif("invalid_wif_string")
    
    def test_key_equality(self):
        """Same WIF should produce equal keys"""
        k1 = Key.from_wif(ALICE_WIF)
        k2 = Key.from_wif(ALICE_WIF)
        assert k1 == k2
    
    def test_key_inequality(self):
        """Different keys should not be equal"""
        alice = Key.from_wif(ALICE_WIF)
        bob = Key.from_wif(BOB_WIF)
        assert alice != bob


# ============================================================================
# Unit Tests - TapTree & TaprootProgram
# ============================================================================

class TestTapTree:
    """Test TapTree builder and TaprootProgram"""
    
    @pytest.fixture
    def keys(self):
        """Provide test keys"""
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }
    
    @pytest.fixture
    def program(self, keys):
        """Build the standard 4-leaf program"""
        return (TapTree(internal_key=keys["alice"])
            .hashlock("helloworld", label="hash")
            .multisig(2, [keys["alice"], keys["bob"]], label="2of2")
            .timelock(blocks=2, then=keys["bob"], label="csv")
            .checksig(keys["bob"], label="bob")
        ).build()
    
    def test_address_generation(self, program):
        """Address must match expected value"""
        assert program.address == EXPECTED_ADDRESS
    
    def test_leaf_count(self, program):
        """Should have 4 leaves"""
        assert program.num_leaves == 4
    
    def test_leaf_labels(self, program):
        """Leaves should be accessible by label"""
        assert program.leaves == ["hash", "2of2", "csv", "bob"]
    
    def test_leaf_by_label(self, program):
        """Each leaf should be retrievable"""
        hash_leaf = program.leaf("hash")
        assert hash_leaf.script_type == "HASHLOCK"
        
        multisig_leaf = program.leaf("2of2")
        assert multisig_leaf.script_type == "MULTISIG"
        
        csv_leaf = program.leaf("csv")
        assert csv_leaf.script_type == "CSV_TIMELOCK"
        
        bob_leaf = program.leaf("bob")
        assert bob_leaf.script_type == "CHECKSIG"
    
    def test_leaf_by_index(self, program):
        """Leaves should also be accessible by index"""
        assert program.leaf(0).label == "hash"
        assert program.leaf(1).label == "2of2"
        assert program.leaf(2).label == "csv"
        assert program.leaf(3).label == "bob"
    
    def test_invalid_leaf_label(self, program):
        """Invalid label should raise KeyError"""
        with pytest.raises(KeyError):
            program.leaf("nonexistent")
    
    def test_invalid_leaf_index(self, program):
        """Invalid index should raise KeyError"""
        with pytest.raises(KeyError):
            program.leaf(99)
    
    def test_visualize(self, program):
        """Visualize should return tree structure"""
        viz = program.visualize()
        assert "Merkle Root" in viz
        assert "[hash]" in viz
        assert "[2of2]" in viz
        assert "[csv]" in viz
        assert "[bob]" in viz


# ============================================================================
# Unit Tests - 2-Leaf TapTree
# ============================================================================

class TestTwoLeafTree:
    """Test 2-leaf Taproot tree (hashlock + multisig)"""

    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }

    @pytest.fixture
    def program(self, keys):
        """Build a 2-leaf program: hashlock + 2-of-2 multisig"""
        return (TapTree(internal_key=keys["alice"])
            .hashlock("mysecret", label="hash")
            .multisig(2, [keys["alice"], keys["bob"]], label="2of2")
        ).build()

    def test_address_is_valid(self, program):
        """2-leaf tree should produce a valid tb1p address"""
        assert program.address.startswith("tb1p")
        assert len(program.address) == 62

    def test_leaf_count(self, program):
        """Should have 2 leaves"""
        assert program.num_leaves == 2

    def test_leaf_labels(self, program):
        """Leaves should be hash and 2of2"""
        assert program.leaves == ["hash", "2of2"]

    def test_leaf_types(self, program):
        """Each leaf should have correct script type"""
        assert program.leaf("hash").script_type == "HASHLOCK"
        assert program.leaf("2of2").script_type == "MULTISIG"

    def test_visualize(self, program):
        """Visualize should show 2-leaf tree"""
        viz = program.visualize()
        assert "Merkle Root" in viz
        assert "[hash]" in viz
        assert "[2of2]" in viz

    def test_hashlock_spend(self, program):
        """Hashlock spend should build on 2-leaf tree"""
        tx = (program.spend("hash")
            .from_utxo("a" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .unlock(preimage="mysecret")
            .build())

        assert tx.hex is not None
        assert len(tx.txid) == 64
        assert tx.fee == 500

    def test_multisig_spend(self, program, keys):
        """Multisig spend should build on 2-leaf tree"""
        tx = (program.spend("2of2")
            .from_utxo("b" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .sign(keys["alice"], keys["bob"])
            .build())

        assert tx.hex is not None
        assert tx.fee == 500

    def test_keypath_spend(self, program, keys):
        """Key-path spend should also work on 2-leaf tree"""
        tx = (program.keypath()
            .from_utxo("c" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .sign(keys["alice"])
            .build())

        assert tx.hex is not None
        assert tx.fee == 500


# ============================================================================
# Unit Tests - SpendBuilder
# ============================================================================

class TestSpendBuilder:
    """Test SpendBuilder construction (without broadcast)"""
    
    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }
    
    @pytest.fixture
    def program(self, keys):
        return (TapTree(internal_key=keys["alice"])
            .hashlock("helloworld", label="hash")
            .multisig(2, [keys["alice"], keys["bob"]], label="2of2")
            .timelock(blocks=2, then=keys["bob"], label="csv")
            .checksig(keys["bob"], label="bob")
        ).build()
    
    def test_hashlock_spend_build(self, program):
        """Hashlock spend should build successfully"""
        tx = (program.spend("hash")
            .from_utxo("a" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .unlock(preimage="helloworld")
            .build())
        
        assert tx.hex is not None
        assert len(tx.txid) == 64
        assert tx.fee == 500
    
    def test_multisig_spend_build(self, program, keys):
        """Multisig spend should build successfully"""
        tx = (program.spend("2of2")
            .from_utxo("b" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .sign(keys["alice"], keys["bob"])
            .build())
        
        assert tx.hex is not None
        assert tx.fee == 500
    
    def test_checksig_spend_build(self, program, keys):
        """Checksig spend should build successfully"""
        tx = (program.spend("bob")
            .from_utxo("c" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .sign(keys["bob"])
            .build())
        
        assert tx.hex is not None
        assert tx.fee == 500
    
    def test_csv_spend_build(self, program, keys):
        """CSV spend should build successfully (broadcast may fail if timelock not met)"""
        tx = (program.spend("csv")
            .from_utxo("d" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .sign(keys["bob"])
            .build())
        
        assert tx.hex is not None
        assert tx.fee == 500
    
    def test_keypath_spend_build(self, program, keys):
        """Key path spend should build successfully"""
        tx = (program.keypath()
            .from_utxo("e" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .sign(keys["alice"])
            .build())
        
        assert tx.hex is not None
        assert tx.fee == 500
    
    def test_from_utxos_single_equiv_to_from_utxo(self, program, keys):
        """from_utxos([(txid,vout,sats)]) should match from_utxo() for single UTXO"""
        tx1 = (program.spend("hash")
            .from_utxo("a" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .unlock(preimage="helloworld")
            .build())
        tx2 = (program.spend("hash")
            .from_utxos([("a" * 64, 0, 1000)])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .unlock(preimage="helloworld")
            .build())
        assert tx1.txid == tx2.txid
        assert tx1.fee == tx2.fee == 500
    
    def test_from_utxos_multi_builds(self, program, keys):
        """from_utxos with 2 UTXOs should build successfully"""
        tx = (program.spend("hash")
            .from_utxos([("a" * 64, 0, 600), ("b" * 64, 1, 400)])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 800)
            .unlock(preimage="helloworld")
            .build())
        assert tx.hex is not None
        assert tx.fee == 200  # 1000 total in - 800 out
        assert len(tx.txid) == 64


# ============================================================================
# Integration Tests - Verified Transactions
# ============================================================================

class TestVerifiedTransactions:
    """
    These tests verify that we can reproduce the exact transactions
    that were successfully broadcast to testnet.
    
    Note: These require the exact same inputs, so they serve as
    regression tests to ensure the signing logic doesn't change.
    """
    
    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }
    
    @pytest.fixture
    def program(self, keys):
        return (TapTree(internal_key=keys["alice"])
            .hashlock("helloworld", label="hash")
            .multisig(2, [keys["alice"], keys["bob"]], label="2of2")
            .timelock(blocks=2, then=keys["bob"], label="csv")
            .checksig(keys["bob"], label="bob")
        ).build()
    
    def test_hashlock_txid_match(self, program):
        """Hashlock transaction should produce exact TXID"""
        info = VERIFIED_TXS["hashlock"]
        
        tx = (program.spend("hash")
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", info["output_sats"])
            .unlock(preimage=info["preimage"])
            .build())
        
        assert tx.txid == info["txid"]
        assert tx.fee == info["fee"]
    
    def test_multisig_txid_match(self, program, keys):
        """Multisig transaction should produce exact TXID"""
        info = VERIFIED_TXS["multisig"]
        
        tx = (program.spend("2of2")
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", info["output_sats"])
            .sign(keys["alice"], keys["bob"])
            .build())
        
        assert tx.txid == info["txid"]
        assert tx.fee == info["fee"]
    
    def test_checksig_txid_match(self, program, keys):
        """Checksig transaction should produce exact TXID"""
        info = VERIFIED_TXS["checksig_bob"]
        
        tx = (program.spend("bob")
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", info["output_sats"])
            .sign(keys["bob"])
            .build())
        
        assert tx.txid == info["txid"]
        assert tx.fee == info["fee"]
    
    def test_keypath_txid_match(self, program, keys):
        """Key path transaction should produce exact TXID"""
        info = VERIFIED_TXS["keypath"]
        
        tx = (program.keypath()
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", info["output_sats"])
            .sign(keys["alice"])
            .build())
        
        assert tx.txid == info["txid"]
        assert tx.fee == info["fee"]
    
    def test_csv_txid_match(self, program, keys):
        """CSV timelock transaction should produce exact TXID"""
        info = VERIFIED_TXS["csv_timelock"]
        
        tx = (program.spend("csv")
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", info["output_sats"])
            .sign(keys["bob"])
            .build())
        
        assert tx.txid == info["txid"]
        assert tx.fee == info["fee"]


# ============================================================================
# Integration Tests - 2-Leaf Verified Transactions
# ============================================================================

TWO_LEAF_VERIFIED_TXS = {
    "hashlock": {
        "txid": "9e2767bd0df1b6a1cbb7d389cea29f5031dd0a064c89688e1348ca48c2e199ac",
        "input_txid": "5cb673175a28dd0750f18cdfd8323418630f8edf2f08c773fc64a563362290a5",
        "input_vout": 1,
        "input_sats": 3000,
        "output_sats": 2500,
        "fee": 500,
        "preimage": "mysecret2026",
    },
    "multisig": {
        "txid": "e17afe675d83e42480d25255e3b86b271f5a0ad5e8b0d64fd5409c60840263e7",
        "input_txid": "b892a615409762b5f1893bafd43a2286b60ca79511478501ef743fcbeaa79c15",
        "input_vout": 0,
        "input_sats": 2888,
        "output_sats": 2388,
        "fee": 500,
    },
}

DEST_ADDRESS = "tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne"


class TestTwoLeafVerifiedTransactions:
    """
    Verify exact TXID reproduction for 2-leaf Taproot tree transactions.
    These transactions were broadcast to testnet on 2026-02-10.
    """

    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }

    @pytest.fixture
    def program(self, keys):
        return (TapTree(internal_key=keys["alice"])
            .hashlock("mysecret2026", label="hash")
            .multisig(2, [keys["alice"], keys["bob"]], label="2of2")
        ).build()

    def test_two_leaf_hashlock_txid_match(self, program):
        """2-leaf hashlock transaction should produce exact TXID"""
        info = TWO_LEAF_VERIFIED_TXS["hashlock"]

        tx = (program.spend("hash")
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to(DEST_ADDRESS, info["output_sats"])
            .unlock(preimage=info["preimage"])
            .build())

        assert tx.txid == info["txid"]
        assert tx.fee == info["fee"]

    def test_two_leaf_multisig_txid_match(self, program, keys):
        """2-leaf multisig transaction should produce exact TXID"""
        info = TWO_LEAF_VERIFIED_TXS["multisig"]

        tx = (program.spend("2of2")
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to(DEST_ADDRESS, info["output_sats"])
            .sign(keys["alice"], keys["bob"])
            .build())

        assert tx.txid == info["txid"]
        assert tx.fee == info["fee"]


# ============================================================================
# PSBT Flow Tests
# ============================================================================

class TestPsbtFlow:
    """Test PSBT create → sign → finalize → extract flow."""

    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }

    @pytest.fixture
    def program(self, keys):
        return (TapTree(internal_key=keys["alice"])
            .hashlock("helloworld", label="hash")
            .multisig(2, [keys["alice"], keys["bob"]], label="2of2")
        ).build()

    def test_psbt_multisig_roundtrip(self, program, keys):
        """PSBT multisig flow should build valid transaction"""
        psbt = (program.spend("2of2")
            .from_utxo("b" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .to_psbt())

        psbt.sign_with(keys["alice"], 0)
        psbt.sign_with(keys["bob"], 0)
        psbt.finalize()
        tx = psbt.extract_transaction()

        assert tx is not None
        assert hasattr(tx, 'get_txid') or hasattr(tx, 'txid')
        txid = tx.get_txid() if hasattr(tx, 'get_txid') else tx.txid
        assert len(txid) == 64
        assert txid == txid.lower()

    def test_psbt_multisig_txid_matches_direct_build(self, program, keys):
        """PSBT multisig flow should produce same TXID as direct .sign().build()"""
        # Direct build
        tx_direct = (program.spend("2of2")
            .from_utxo("b" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .sign(keys["alice"], keys["bob"])
            .build())

        # PSBT flow
        psbt = (program.spend("2of2")
            .from_utxo("b" * 64, 0, sats=1000)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
            .to_psbt())
        psbt.sign_with(keys["alice"], 0)
        psbt.sign_with(keys["bob"], 0)
        psbt.finalize()
        tx_psbt = psbt.extract_transaction()

        txid_psbt = tx_psbt.get_txid() if hasattr(tx_psbt, 'get_txid') else tx_psbt.txid
        assert txid_psbt == tx_direct.txid
        assert tx_direct.fee == 500

    def test_psbt_verified_multisig_txid_match(self, program, keys):
        """PSBT multisig with verified UTXO should produce exact TXID"""
        info = VERIFIED_TXS["multisig"]

        psbt = (program.spend("2of2")
            .from_utxo(info["input_txid"], info["input_vout"], sats=info["input_sats"])
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", info["output_sats"])
            .to_psbt())
        psbt.sign_with(keys["alice"], 0)
        psbt.sign_with(keys["bob"], 0)
        psbt.finalize()
        tx = psbt.extract_transaction()

        txid = tx.get_txid() if hasattr(tx, 'get_txid') else tx.txid
        assert txid == info["txid"]

    def test_psbt_base64_roundtrip(self, program, keys):
        """PSBT to_base64 → from_base64 should preserve signing capability"""
        psbt1 = (program.spend("2of2")
            .from_utxo("c" * 64, 0, sats=800)
            .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 300)
            .to_psbt())
        b64 = psbt1.to_base64()
        psbt2 = Psbt.from_base64(b64)
        psbt2.sign_with(keys["alice"], 0)
        psbt2.sign_with(keys["bob"], 0)
        psbt2.finalize()
        tx = psbt2.extract_transaction()
        assert tx is not None
        txid = tx.get_txid() if hasattr(tx, 'get_txid') else tx.txid
        assert len(txid) == 64


# ============================================================================
# quick_transfer taproot path (v0.2 flow)
# ============================================================================

class TestQuickTransferTaproot:
    """Test quick_transfer taproot path uses v0.2 and auto UTXO selection."""

    def test_quick_transfer_taproot_returns_none_when_no_utxos(self):
        """quick_transfer(taproot) returns None when no UTXOs available"""
        with patch("btcaaron.network.utxo.fetch_utxos", return_value=[]):
            result = quick_transfer(
                ALICE_WIF, "taproot",
                "tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209",
                500, fee=300, debug=False
            )
        assert result is None

    def test_quick_transfer_taproot_returns_none_when_insufficient(self):
        """quick_transfer(taproot) returns None when balance < amount + fee"""
        with patch("btcaaron.network.utxo.fetch_utxos", return_value=[
            {"txid": "a" * 64, "vout": 0, "amount": 400}
        ]):
            result = quick_transfer(
                ALICE_WIF, "taproot",
                "tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209",
                500, fee=300, debug=False
            )
        assert result is None


# ============================================================================
# Duplicate Label Rejection Tests
# ============================================================================

class TestDuplicateLabelRejection:
    """Test that duplicate leaf labels are rejected at build time."""

    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }

    def test_duplicate_labels_raise_build_error(self, keys):
        """Duplicate labels should raise BuildError"""
        from btcaaron.errors import BuildError
        with pytest.raises(BuildError, match="Duplicate leaf labels"):
            (TapTree(internal_key=keys["alice"])
                .checksig(keys["bob"], label="same")
                .checksig(keys["bob"], label="same")
            ).build()

    def test_unique_labels_work(self, keys):
        """Unique labels should build fine"""
        prog = (TapTree(internal_key=keys["alice"])
            .checksig(keys["bob"], label="a")
            .checksig(keys["bob"], label="b")
        ).build()
        assert prog.num_leaves == 2


# ============================================================================
# Balanced Tree Builder Tests
# ============================================================================

class TestBalancedTree:
    """Test that TapTree supports arbitrary leaf counts, not just 1/2/4."""

    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif(ALICE_WIF),
            "bob": Key.from_wif(BOB_WIF),
        }

    def test_three_leaf_tree(self, keys):
        """3-leaf tree should build successfully"""
        prog = (TapTree(internal_key=keys["alice"])
            .hashlock("secret", label="hash")
            .checksig(keys["bob"], label="bob")
            .timelock(blocks=10, then=keys["bob"], label="csv")
        ).build()
        assert prog.address.startswith("tb1p")
        assert prog.num_leaves == 3
        assert set(prog.leaves) == {"hash", "bob", "csv"}

    def test_five_leaf_tree(self, keys):
        """5-leaf tree should build successfully"""
        prog = (TapTree(internal_key=keys["alice"])
            .hashlock("a", label="h1")
            .hashlock("b", label="h2")
            .checksig(keys["bob"], label="sig")
            .timelock(blocks=5, then=keys["bob"], label="csv")
            .multisig(2, [keys["alice"], keys["bob"]], label="multi")
        ).build()
        assert prog.address.startswith("tb1p")
        assert prog.num_leaves == 5

    def test_six_and_eight_leaf_trees(self, keys):
        """6 and 8 leaf trees should build successfully"""
        for n in [6, 8]:
            tree = TapTree(internal_key=keys["alice"])
            for i in range(n):
                tree = tree.checksig(keys["bob"], label=f"leaf{i}")
            prog = tree.build()
            assert prog.address.startswith("tb1p")
            assert prog.num_leaves == n

    def test_existing_1_2_4_unchanged(self, keys):
        """1, 2, 4 leaf trees should still produce valid addresses"""
        for n in [1, 2, 4]:
            tree = TapTree(internal_key=keys["alice"])
            for i in range(n):
                tree = tree.checksig(keys["bob"], label=f"l{i}")
            prog = tree.build()
            assert prog.address.startswith("tb1p")
            assert prog.num_leaves == n


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])