#!/usr/bin/env python3
"""
Two-leaf Taproot (paper §6.2): a SHA256 hashlock + a simple P2PK leaf at depth 1.
Case 2-A = hashlock path, Case 2-B = P2PK path. Reuses helpers from four_leaf_lib.
"""
import hashlib
from bitcoinutils.script import Script
from bitcoinutils.transactions import TxWitnessInput
from bitcoinutils.utils import ControlBlock
from four_leaf_lib import PREIMAGE, _new_tx


def build_tree(alice_pub, bob_pub):
    hash0 = hashlib.sha256(PREIMAGE.encode()).hexdigest()
    s_hash = Script(['OP_SHA256', hash0, 'OP_EQUALVERIFY', 'OP_TRUE'])
    s_p2pk = Script([bob_pub.to_x_only_hex(), 'OP_CHECKSIG'])
    tree = [s_hash, s_p2pk]                       # depth-1, two leaves
    return {'hash': s_hash, 'p2pk': s_p2pk}, tree


def address(alice_pub, tree):
    return alice_pub.get_taproot_address(tree)


def spend(case, prev_txid, vout, in_sats, out_sats, dest,
          alice, bob, scripts, tree, taddr):
    """case in {'2A','2B'} -> hashlock / p2pk."""
    alice_pub = alice.get_public_key()
    if case == '2A':                              # hashlock
        tx, _ = _new_tx(prev_txid, vout, in_sats, out_sats, dest)
        cb = ControlBlock(alice_pub, tree, 0, is_odd=taddr.is_odd())
        tx.witnesses.append(TxWitnessInput([
            PREIMAGE.encode().hex(), scripts['hash'].to_hex(), cb.to_hex()]))
        return tx.serialize()
    if case == '2B':                              # p2pk (Bob)
        tx, _ = _new_tx(prev_txid, vout, in_sats, out_sats, dest)
        cb = ControlBlock(alice_pub, tree, 1, is_odd=taddr.is_odd())
        sb = bob.sign_taproot_input(tx, 0, [taddr.to_script_pub_key()], [in_sats],
                                    script_path=True, tapleaf_script=scripts['p2pk'], tweak=False)
        tx.witnesses.append(TxWitnessInput([sb, scripts['p2pk'].to_hex(), cb.to_hex()]))
        return tx.serialize()
    raise ValueError(case)
