#!/usr/bin/env python3
"""
Four-Leaf Taproot experiment — btcaaron DECLARATIVE edition.

This is the same experiment as `four_leaf_lib.py` (the python-bitcoin-utils
reference implementation that produced the on-chain testnet3/signet/mainnet
TXIDs), re-expressed through btcaaron's high-level TapTree / SpendBuilder API.

VERIFIED EQUIVALENT: with the same two keys this builds the *identical* Taproot
address as the on-chain signet four-leaf address
    tb1pf5rhd89h6hpgcf9eah2xxp4wnn9qzadlp56yj2vck8uu86erre4qg9vcse
and all five spend paths pass testmempoolaccept on regtest. The leaf templates
are byte-for-byte identical:

  hash : OP_SHA256 <sha256("helloworld")> OP_EQUALVERIFY OP_TRUE     (.hashlock)
  2of2 : OP_0 <alice> OP_CHECKSIGADD <bob> OP_CHECKSIGADD OP_2 OP_EQUAL (.multisig)
  csv  : <seq=2> OP_CHECKSEQUENCEVERIFY OP_DROP <bob> OP_CHECKSIG     (.timelock)
  sig  : <bob> OP_CHECKSIG                                            (.checksig)
  + key path (Alice internal key)

Tree (depth 2, balanced):       Merkle Root
                               /            \
                          Branch0          Branch1
                          /     \          /     \
                       hash   2of2      csv     sig
"""
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from btcaaron import Key, TapTree

PREIMAGE = "helloworld"
RELATIVE_BLOCKS = 2          # CSV path: spendable after 2 blocks

# label order matters: it fixes leaf positions == four_leaf_lib script0..3
LABELS = ["hash", "2of2", "csv", "sig"]


def init(network):
    """network in {'regtest','testnet','signet','mainnet'}"""
    setup(network)


def make_keys(alice_wif=None, bob_wif=None):
    """Load btcaaron Keys from WIF, or mint fresh ones (call AFTER init())."""
    aw = alice_wif or PrivateKey().to_wif()
    bw = bob_wif or PrivateKey().to_wif()
    return Key.from_wif(aw), Key.from_wif(bw)


def build_program(alice, bob):
    """Return a built TaprootProgram (declarative) — same address as four_leaf_lib."""
    return (TapTree(internal_key=alice)
            .hashlock(PREIMAGE,            label="hash")
            .multisig(2, [alice, bob],     label="2of2")
            .timelock(blocks=RELATIVE_BLOCKS, then=bob, label="csv")
            .checksig(bob,                 label="sig")
            ).build()


def spend(program, path, prev_txid, vout, in_sats, out_sats, dest, alice, bob):
    """Build one spend tx via btcaaron; return raw hex.
    path in {'keypath','hashlock','multisig','csv','sig'}."""
    if path == "keypath":
        b = program.keypath().from_utxo(prev_txid, vout, sats=in_sats).to(dest, out_sats)
        return b.sign(alice).build().hex

    if path == "hashlock":
        b = program.spend("hash").from_utxo(prev_txid, vout, sats=in_sats).to(dest, out_sats)
        return b.unlock(preimage=PREIMAGE).build().hex

    if path == "multisig":
        b = program.spend("2of2").from_utxo(prev_txid, vout, sats=in_sats).to(dest, out_sats)
        return b.sign(alice, bob).build().hex   # btcaaron auto-orders by pubkey

    if path == "csv":
        b = program.spend("csv").from_utxo(prev_txid, vout, sats=in_sats).to(dest, out_sats)
        return b.sign(bob).build().hex          # CSV nSequence set automatically

    if path == "sig":
        b = program.spend("sig").from_utxo(prev_txid, vout, sats=in_sats).to(dest, out_sats)
        return b.sign(bob).build().hex

    raise ValueError(f"unknown path {path}")


# the five spends in paper order (key path + 4 script paths)
PATHS = ["keypath", "hashlock", "multisig", "csv", "sig"]
