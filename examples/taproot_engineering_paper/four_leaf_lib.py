#!/usr/bin/env python3
"""
Four-Leaf Taproot experiment library — parameterized over network/keys/UTXO/fee/dest.

Faithful port of mastering-taproot/code/chapter08 (the PROVEN testnet logic),
refactored into reusable functions so the SAME code path runs on
regtest (rehearsal) -> mainnet (live), changing only NETWORK + keys + UTXOs.

Tree (depth 2):           Merkle Root
                         /            \
                    Branch0          Branch1
                    /     \          /     \
               Script0  Script1  Script2  Script3
               (hash)   (multi)  (CSV)    (sig)        + Key Path (Alice)
"""
import hashlib
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2trAddress, P2wpkhAddress
from bitcoinutils.script import Script
from bitcoinutils.transactions import (Transaction, TxInput, TxOutput,
                                       TxWitnessInput, Sequence)
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
from bitcoinutils.utils import to_satoshis, ControlBlock

PREIMAGE = "helloworld"
RELATIVE_BLOCKS = 2          # CSV path: spendable after 2 blocks


def init(network):
    """network in {'regtest','testnet','signet','mainnet'}"""
    setup(network)


def make_keys(alice_wif=None, bob_wif=None):
    """Load keys from WIF, or generate fresh random ones (call AFTER init())."""
    alice = PrivateKey(alice_wif) if alice_wif else PrivateKey()
    bob = PrivateKey(bob_wif) if bob_wif else PrivateKey()
    return alice, bob


def build_tree(alice_pub, bob_pub):
    """Return (scripts dict, tree) — identical structure to chapter08."""
    hash0 = hashlib.sha256(PREIMAGE.encode()).hexdigest()
    script0 = Script(['OP_SHA256', hash0, 'OP_EQUALVERIFY', 'OP_TRUE'])
    script1 = Script(['OP_0', alice_pub.to_x_only_hex(), 'OP_CHECKSIGADD',
                      bob_pub.to_x_only_hex(), 'OP_CHECKSIGADD', 'OP_2', 'OP_EQUAL'])
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, RELATIVE_BLOCKS)
    script2 = Script([seq.for_script(), 'OP_CHECKSEQUENCEVERIFY', 'OP_DROP',
                      bob_pub.to_x_only_hex(), 'OP_CHECKSIG'])
    script3 = Script([bob_pub.to_x_only_hex(), 'OP_CHECKSIG'])
    tree = [[script0, script1], [script2, script3]]
    return {'0': script0, '1': script1, '2': script2, '3': script3}, tree


def address(alice_pub, tree):
    return alice_pub.get_taproot_address(tree)


def _dest_spk(addr):
    """Build scriptPubKey for a P2TR (bc1p/tb1p/bcrt1p) or P2WPKH (bc1q/...) dest."""
    a = addr.strip()
    if a[:4] in ('bc1p', 'tb1p') or a.startswith('bcrt1p'):
        return P2trAddress(a).to_script_pub_key()
    if a[:4] in ('bc1q', 'tb1q') or a.startswith('bcrt1q'):
        return P2wpkhAddress(a).to_script_pub_key()
    raise ValueError(f"unsupported destination address type: {addr}")


def _new_tx(prev_txid, vout, in_sats, out_sats, dest, sequence=None):
    txin = TxInput(prev_txid, vout) if sequence is None else TxInput(prev_txid, vout, sequence=sequence)
    if sequence is None:
        txin.sequence = (0xfffffffd).to_bytes(4, 'little')   # RBF
    txout = TxOutput(out_sats, _dest_spk(dest))
    return Transaction([txin], [txout], has_segwit=True), txin


def spend(path, prev_txid, vout, in_sats, out_sats, dest,
          alice, bob, scripts, tree, taddr):
    """Build one spend tx; return raw hex. path in {'hashlock','multisig','csv','sig','keypath'}."""
    alice_pub = alice.get_public_key()
    spk = [taddr.to_script_pub_key()]
    amts = [in_sats]

    if path == 'keypath':
        tx, _ = _new_tx(prev_txid, vout, in_sats, out_sats, dest)
        sig = alice.sign_taproot_input(tx, 0, spk, amts,
                                       script_path=False, tapleaf_scripts=tree)
        tx.witnesses.append(TxWitnessInput([sig]))
        return tx.serialize()

    if path == 'hashlock':
        tx, _ = _new_tx(prev_txid, vout, in_sats, out_sats, dest)
        cb = ControlBlock(alice_pub, tree, 0, is_odd=taddr.is_odd())
        tx.witnesses.append(TxWitnessInput([
            PREIMAGE.encode().hex(), scripts['0'].to_hex(), cb.to_hex()]))
        return tx.serialize()

    if path == 'multisig':
        tx, _ = _new_tx(prev_txid, vout, in_sats, out_sats, dest)
        cb = ControlBlock(alice_pub, tree, 1, is_odd=taddr.is_odd())
        sa = alice.sign_taproot_input(tx, 0, spk, amts, script_path=True,
                                      tapleaf_script=scripts['1'], tweak=False)
        sb = bob.sign_taproot_input(tx, 0, spk, amts, script_path=True,
                                    tapleaf_script=scripts['1'], tweak=False)
        # witness order: Bob then Alice (LIFO -> Alice consumed first, matches script order)
        tx.witnesses.append(TxWitnessInput([sb, sa, scripts['1'].to_hex(), cb.to_hex()]))
        return tx.serialize()

    if path == 'csv':
        seq_in = Sequence(TYPE_RELATIVE_TIMELOCK, RELATIVE_BLOCKS).for_input_sequence()
        tx, _ = _new_tx(prev_txid, vout, in_sats, out_sats, dest, sequence=seq_in)
        cb = ControlBlock(alice_pub, tree, 2, is_odd=taddr.is_odd())
        sb = bob.sign_taproot_input(tx, 0, spk, amts, script_path=True,
                                    tapleaf_script=scripts['2'], tweak=False)
        tx.witnesses.append(TxWitnessInput([sb, scripts['2'].to_hex(), cb.to_hex()]))
        return tx.serialize()

    if path == 'sig':
        tx, _ = _new_tx(prev_txid, vout, in_sats, out_sats, dest)
        cb = ControlBlock(alice_pub, tree, 3, is_odd=taddr.is_odd())
        sb = bob.sign_taproot_input(tx, 0, spk, amts, script_path=True,
                                    tapleaf_script=scripts['3'], tweak=False)
        tx.witnesses.append(TxWitnessInput([sb, scripts['3'].to_hex(), cb.to_hex()]))
        return tx.serialize()

    raise ValueError(f"unknown path {path}")


# convenience: the five spends in paper order (key path + 4 script paths)
PATHS = ['keypath', 'hashlock', 'multisig', 'csv', 'sig']
