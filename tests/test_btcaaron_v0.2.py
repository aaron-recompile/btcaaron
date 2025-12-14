"""
btcaaron v0.2.0 Test Suite

This file contains both unit tests and integration tests with
real testnet transaction records for verification.

Run with: pytest tests/test_btcaaron_v0.2.py -v
"""

import pytest
from btcaaron import Key, TapTree


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
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])