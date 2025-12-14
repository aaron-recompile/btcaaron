#!/usr/bin/env python3
"""
Debug script to test each script type separately
Run this from your btcaaron project root
"""

from bitcoinutils.setup import setup
from bitcoinutils.script import Script
from bitcoinutils.transactions import Sequence
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
from bitcoinutils.keys import PrivateKey
import hashlib

setup('testnet')

# Setup keys
alice_priv = PrivateKey("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob_priv = PrivateKey("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")
alice_pub = alice_priv.get_public_key()
bob_pub = bob_priv.get_public_key()

alice_xonly = alice_pub.to_x_only_hex()
bob_xonly = bob_pub.to_x_only_hex()

print("=" * 60)
print("DEBUG: Testing each script type")
print("=" * 60)
print(f"Alice x-only pubkey: {alice_xonly}")
print(f"Bob x-only pubkey: {bob_xonly}")
print()

# Test 1: HASHLOCK
print("[1] Testing HASHLOCK...")
try:
    preimage = "helloworld"
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    print(f"    Preimage hash: {preimage_hash}")
    
    ops = ['OP_SHA256', preimage_hash, 'OP_EQUALVERIFY', 'OP_TRUE']
    print(f"    Ops: {ops}")
    
    script = Script(ops)
    hex_result = script.to_hex()
    print(f"    ✓ HASHLOCK OK: {hex_result[:40]}...")
except Exception as e:
    print(f"    ✗ HASHLOCK FAILED: {e}")
print()

# Test 2: CHECKSIG
print("[2] Testing CHECKSIG...")
try:
    ops = [bob_xonly, 'OP_CHECKSIG']
    print(f"    Ops: {ops}")
    
    script = Script(ops)
    hex_result = script.to_hex()
    print(f"    ✓ CHECKSIG OK: {hex_result[:40]}...")
except Exception as e:
    print(f"    ✗ CHECKSIG FAILED: {e}")
print()

# Test 3: MULTISIG
print("[3] Testing MULTISIG...")
try:
    ops = [
        "OP_0",
        alice_xonly,
        "OP_CHECKSIGADD",
        bob_xonly,
        "OP_CHECKSIGADD",
        "OP_2",
        "OP_EQUAL"
    ]
    print(f"    Ops: {ops}")
    
    script = Script(ops)
    hex_result = script.to_hex()
    print(f"    ✓ MULTISIG OK: {hex_result[:40]}...")
except Exception as e:
    print(f"    ✗ MULTISIG FAILED: {e}")
print()

# Test 4: CSV_TIMELOCK
print("[4] Testing CSV_TIMELOCK...")
try:
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, 2)
    seq_for_script = seq.for_script()
    print(f"    seq.for_script() = {seq_for_script} (type: {type(seq_for_script).__name__})")
    
    ops = [
        seq_for_script,
        "OP_CHECKSEQUENCEVERIFY",
        "OP_DROP",
        bob_xonly,
        "OP_CHECKSIG"
    ]
    print(f"    Ops: {ops}")
    
    script = Script(ops)
    hex_result = script.to_hex()
    print(f"    ✓ CSV_TIMELOCK OK: {hex_result[:40]}...")
except Exception as e:
    print(f"    ✗ CSV_TIMELOCK FAILED: {e}")
print()

# Test 5: Full 4-leaf tree (like Chapter 8)
print("[5] Testing full 4-leaf tree creation...")
try:
    preimage = "helloworld"
    hash0 = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    
    script0 = Script(['OP_SHA256', hash0, 'OP_EQUALVERIFY', 'OP_TRUE'])
    
    script1 = Script([
        "OP_0",
        alice_pub.to_x_only_hex(),
        "OP_CHECKSIGADD",
        bob_pub.to_x_only_hex(),
        "OP_CHECKSIGADD",
        "OP_2",
        "OP_EQUAL"
    ])
    
    seq = Sequence(TYPE_RELATIVE_TIMELOCK, 2)
    script2 = Script([
        seq.for_script(),
        "OP_CHECKSEQUENCEVERIFY",
        "OP_DROP",
        bob_pub.to_x_only_hex(),
        "OP_CHECKSIG"
    ])
    
    script3 = Script([bob_pub.to_x_only_hex(), "OP_CHECKSIG"])
    
    tree = [[script0, script1], [script2, script3]]
    taproot_address = alice_pub.get_taproot_address(tree)
    
    print(f"    ✓ Tree created successfully!")
    print(f"    Address: {taproot_address.to_string()}")
    print(f"    Expected: tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q")
    print(f"    Match: {taproot_address.to_string() == 'tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q'}")
except Exception as e:
    import traceback
    print(f"    ✗ FAILED: {e}")
    traceback.print_exc()

print()
print("=" * 60)
print("DEBUG complete")
print("=" * 60)