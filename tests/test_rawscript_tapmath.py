"""
RawScript and tapmath unit tests

Run with: pytest tests/test_rawscript_tapmath.py -v
"""

import pytest
from btcaaron import Key, TapTree, RawScript


# ============================================================================
# RawScript Tests
# ============================================================================

class TestRawScript:
    """Test RawScript class"""

    def test_to_hex_roundtrip(self):
        """RawScript hex round-trip"""
        hex_str = "76a914" + "00" * 20 + "88ac"
        raw = RawScript(hex_str)
        assert raw.to_hex() == hex_str

    def test_to_bytes_roundtrip(self):
        """RawScript bytes round-trip"""
        hex_str = "ac"  # OP_CHECKSIG
        raw = RawScript(hex_str)
        assert raw.to_bytes() == bytes.fromhex(hex_str)
        assert raw.to_bytes().hex() == hex_str

    def test_to_hex_to_bytes_consistency(self):
        """to_hex and to_bytes must be consistent"""
        hex_str = "76a91400112233445566778899aabbccddeeff0011223388ac"
        raw = RawScript(hex_str)
        assert raw.to_bytes().hex() == raw.to_hex()

    def test_to_asm_returns_hex(self):
        """to_asm returns hex or hex-like display (no parsing for RawScript)"""
        raw = RawScript("ac")
        asm = raw.to_asm()
        assert "ac" in asm

    def test_short_script(self):
        """Single-byte script (OP_CHECKSIG)"""
        raw = RawScript("ac")
        assert raw.to_hex() == "ac"
        assert raw.to_bytes() == b"\xac"
        assert len(raw.to_bytes()) == 1


# ============================================================================
# tapmath Tests
# ============================================================================

class TestTapmath:
    """Test tapmath module functions"""

    def test_tapleaf_hash_length(self):
        """tapleaf_hash returns 32 bytes"""
        from btcaaron.tree.tapmath import tapleaf_hash
        script = bytes.fromhex("ac")  # OP_CHECKSIG
        h = tapleaf_hash(script)
        assert len(h) == 32

    def test_tapleaf_hash_deterministic(self):
        """tapleaf_hash is deterministic"""
        from btcaaron.tree.tapmath import tapleaf_hash
        script = bytes.fromhex("76a914" + "00" * 20 + "88ac")
        h1 = tapleaf_hash(script)
        h2 = tapleaf_hash(script)
        assert h1 == h2

    def test_tapbranch_hash(self):
        """tapbranch_hash combines two 32-byte hashes"""
        from btcaaron.tree.tapmath import tapleaf_hash, tapbranch_hash
        left = tapleaf_hash(b"\xac")
        right = tapleaf_hash(b"\x00")
        branch = tapbranch_hash(left, right)
        assert len(branch) == 32
        assert branch == tapbranch_hash(right, left)  # sorted order

    def test_compute_merkle_root_single_leaf(self):
        """Single leaf: merkle root = tapleaf_hash"""
        from btcaaron.tree.tapmath import tapleaf_hash, compute_merkle_root
        script = bytes.fromhex("ac")
        leaf_hash = tapleaf_hash(script)
        root = compute_merkle_root([leaf_hash])
        assert root == leaf_hash

    def test_compute_merkle_root_two_leaves(self):
        """Two leaves: merkle root = tapbranch of both"""
        from btcaaron.tree.tapmath import tapleaf_hash, tapbranch_hash, compute_merkle_root
        h0 = tapleaf_hash(b"\xac")
        h1 = tapleaf_hash(b"\x00")
        root = compute_merkle_root([h0, h1])
        expected = tapbranch_hash(h0, h1)
        assert root == expected

    def test_compute_merkle_proof_single_leaf(self):
        """Single leaf: proof is empty (list or empty bytes)"""
        from btcaaron.tree.tapmath import tapleaf_hash, compute_merkle_proof
        h = tapleaf_hash(b"\xac")
        proof = compute_merkle_proof([h], 0)
        assert len(proof) == 0

    def test_compute_merkle_proof_two_leaves(self):
        """Two leaves: proof has one 32-byte sibling hash (list or concatenated bytes)"""
        from btcaaron.tree.tapmath import tapleaf_hash, compute_merkle_proof
        h0 = tapleaf_hash(b"\xac")
        h1 = tapleaf_hash(b"\x00")
        proof0 = compute_merkle_proof([h0, h1], 0)
        proof1 = compute_merkle_proof([h0, h1], 1)
        # proof: List[bytes] with 1 elem, or concatenated bytes (32 len)
        sibling0 = proof0[0] if isinstance(proof0, list) else proof0
        sibling1 = proof1[0] if isinstance(proof1, list) else proof1
        assert len(sibling0) == 32
        assert len(sibling1) == 32
        assert sibling0 == h1
        assert sibling1 == h0

    def test_compute_control_block_format(self):
        """control_block: version byte + 32 key + merkle proof"""
        from btcaaron.tree.tapmath import tapleaf_hash, compute_control_block
        internal_key = bytes.fromhex("00" * 32)
        leaf_hashes = [tapleaf_hash(b"\xac"), tapleaf_hash(b"\x00")]
        cb = compute_control_block(internal_key, leaf_hashes, 0, is_odd=False)
        assert len(cb) == 65  # 1 + 32 + 32 (version + key + 1 proof element)
        assert cb[0] in (0xc0, 0xc1)  # leaf version
        assert cb[1:33] == internal_key


# ============================================================================
# RawScript + TapTree Integration
# ============================================================================

class TestRawScriptTapTree:
    """RawScript with TapTree.custom() integration"""

    @pytest.fixture
    def keys(self):
        return {
            "alice": Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT"),
            "bob": Key.from_wif("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG"),
        }

    def test_rawscript_single_leaf_address(self, keys):
        """Single RawScript leaf produces valid tb1p address"""
        # Simple OP_CHECKSIG script as RawScript (avoids bitcoinutils parsing)
        raw = RawScript("ac")  # OP_CHECKSIG
        program = (TapTree(internal_key=keys["alice"])
            .custom(raw, label="raw")
            .build())
        assert program.address.startswith("tb1p")
        assert len(program.address) == 62
        assert program.num_leaves == 1
        assert program.leaf("raw").script_type == "CUSTOM"

    def test_rawscript_control_block(self, keys):
        """RawScript leaf: control_block() returns valid hex"""
        raw = RawScript("ac")
        program = (TapTree(internal_key=keys["alice"])
            .custom(raw, label="raw")
            .build())
        cb_hex = program.control_block("raw")
        assert isinstance(cb_hex, str)
        assert len(cb_hex) % 2 == 0
        cb_bytes = bytes.fromhex(cb_hex)
        assert cb_bytes[0] in (0xc0, 0xc1)
        assert len(cb_bytes) == 33  # version + internal key (single leaf: no merkle proof)

    def test_rawscript_merkle_root(self, keys):
        """RawScript path sets merkle_root"""
        raw = RawScript("ac")
        program = (TapTree(internal_key=keys["alice"])
            .custom(raw, label="raw")
            .build())
        mr = program.merkle_root
        assert mr is not None
        assert len(mr) == 64  # 32 bytes hex
        assert all(c in "0123456789abcdef" for c in mr.lower())
