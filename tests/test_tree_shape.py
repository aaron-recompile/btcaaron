"""
Merkle root, address and drawing must describe the same tree.

For leaf counts that are not a power of two the bitcoin-utils path and the
tapmath (RawScript) path pair leaves differently. These tests pin that the
root reported by the program (and written to PSBT_IN_TAP_MERKLE_ROOT) is the
one the address commits to, for both paths.
"""

import pytest

from btcaaron import Key, TapTree
from btcaaron.script import RawScript

ALICE_WIF = "cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT"


@pytest.fixture(scope="module")
def alice():
    return Key.from_wif(ALICE_WIF)


def _hashlock_tree(key, n):
    t = TapTree(internal_key=key)
    for i in range(n):
        t.hashlock(f"secret{i}", label=f"h{i}")
    return t.build()


def _raw_tree(key, program):
    t = TapTree(internal_key=key)
    for label in program.leaves:
        t.custom(RawScript(program.leaf(label).script_hex), label=label)
    return t.build()


def _address_from_root(key, root):
    return key._internal_pub.get_taproot_address(root).to_string()


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8])
def test_merkle_root_matches_address(alice, n):
    p = _hashlock_tree(alice, n)
    assert _address_from_root(alice, p.merkle_root_bytes()) == p.address
    assert p.merkle_root == p.merkle_root_bytes().hex()


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8])
def test_merkle_root_matches_address_rawscript(alice, n):
    p = _raw_tree(alice, _hashlock_tree(alice, n))
    assert _address_from_root(alice, p.merkle_root_bytes()) == p.address


@pytest.mark.parametrize("n", [3, 5])
def test_psbt_carries_committed_root(alice, n):
    p = _hashlock_tree(alice, n)
    psbt = (p.spend("h0")
            .from_utxo("aa" * 32, 0, sats=10_000)
            .to(p.address, 9_000)
            .unlock(preimage="secret0")
            .to_psbt())
    assert _address_from_root(alice, psbt.inputs[0].tap_merkle_root) == p.address


def test_keypath_only_has_no_root(alice):
    p = TapTree(internal_key=alice).build()
    assert p.merkle_root is None
    assert p.merkle_root_bytes() == bytes(32)


def test_visualize_three_leaves(alice):
    p = _hashlock_tree(alice, 3)
    assert p.visualize() == (
        "Merkle Root\n"
        "├── [h0]\n"
        "└── Branch\n"
        "    ├── [h1]\n"
        "    └── [h2]"
    )


def test_visualize_three_leaves_rawscript(alice):
    p = _raw_tree(alice, _hashlock_tree(alice, 3))
    assert p.visualize() == (
        "Merkle Root\n"
        "├── Branch\n"
        "│   ├── [h0]\n"
        "│   └── [h1]\n"
        "└── [h2]"
    )


@pytest.mark.parametrize("n", [1, 5, 8])
def test_visualize_lists_every_leaf(alice, n):
    viz = _hashlock_tree(alice, n).visualize()
    for i in range(n):
        assert f"[h{i}]" in viz
