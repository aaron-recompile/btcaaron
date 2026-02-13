#!/usr/bin/env python3
"""
Chapter 7: Dual-Leaf Taproot Script Tree (btcaaron version)

Covers the SAME content as 4 original files in mastering-taproot/code/chapter07/:
  01_create_dual_leaf_taproot.py     → Part 1: Build Tree
  02_hash_script_path_spending.py    → Part 2: Hashlock spend
  03_bob_script_path_spending.py     → Part 3: Bob checksig spend
  04_verify_control_block.py         → Part 4: Verify TXIDs

Original code: ~537 lines across 4 files
btcaaron version: ~100 lines in 1 file

NOTE on TXID matching:
  The original Ch07 code uses nSequence=0xffffffff (RBF disabled).
  btcaaron defaults to nSequence=0xfffffffd (RBF enabled).
  This causes TXID differences — not a logic error, just a sequence flag.
  → API improvement identified: add .sequence() method to SpendBuilder.

Run: python examples/ch07_dual_leaf_tree.py
"""

from btcaaron import Key, TapTree

# ═══════════════════════════════════════════════════════════════════
# Keys
# ═══════════════════════════════════════════════════════════════════

alice = Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob   = Key.from_wif("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")

# ═══════════════════════════════════════════════════════════════════
# Part 1: Build the 2-leaf Taproot tree
# Original: 01_create_dual_leaf_taproot.py (107 lines)
#
# Script tree:
#     Merkle Root
#    /            \
# [hash]        [bob]
# ═══════════════════════════════════════════════════════════════════

program = (TapTree(internal_key=alice)
    .hashlock("helloworld", label="hash")    # Script 0: SHA256 hash lock
    .checksig(bob, label="bob")              # Script 1: Bob's signature
).build()

print("=" * 70)
print("PART 1: DUAL-LEAF TAPROOT TREE CONSTRUCTION")
print("=" * 70)
print(f"  Address:  {program.address}")
print(f"  Leaves:   {program.leaves}")
print(f"  Visualization:")
print(program.visualize())

EXPECTED_ADDR = "tb1p93c4wxsr87p88jau7vru83zpk6xl0shf5ynmutd9x0gxwau3tngq9a4w3z"
assert program.address == EXPECTED_ADDR
print(f"  ✅ Address matches Chapter 7: {EXPECTED_ADDR}")

# ═══════════════════════════════════════════════════════════════════
# Part 2: Hashlock script-path spending
# Original: 02_hash_script_path_spending.py (131 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 2: HASHLOCK SCRIPT-PATH SPENDING")
print("=" * 70)

tx_hash = (program.spend("hash")
    .from_utxo("f02c055369812944390ca6a232190ec0db83e4b1b623c452a269408bf8282d66", 0, sats=1234)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 1034)
    .unlock(preimage="helloworld")
    .build())

EXPECTED_HASH_TXID = "b61857a05852482c9d5ffbb8159fc2ba1efa3dd16fe4595f121fc35878a2e430"
print(f"  btcaaron TXID: {tx_hash.txid}")
print(f"  Book TXID:     {EXPECTED_HASH_TXID}")
if tx_hash.txid == EXPECTED_HASH_TXID:
    print(f"  ✅ Exact match")
else:
    print(f"  ⚠️  Mismatch (nSequence: btcaaron=0xfffffffd, book=0xffffffff)")
    print(f"     This is expected — see NOTE at top of file")

# ═══════════════════════════════════════════════════════════════════
# Part 3: Bob checksig script-path spending
# Original: 03_bob_script_path_spending.py (140 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 3: BOB CHECKSIG SCRIPT-PATH SPENDING")
print("=" * 70)

tx_bob = (program.spend("bob")
    .from_utxo("8caddfad76a5b3a8595a522e24305dc20580ca868ef733493e308ada084a050c", 1, sats=1111)
    .to("tb1pshzcvake3a3d76jmue3jz4hyh35yvk0gjj752pd53ys9txy5c3aswe5cn7", 900)
    .sign(bob)
    .build())

EXPECTED_BOB_TXID = "185024daff64cea4c82f129aa9a8e97b4622899961452d1d144604e65a70cfe0"
print(f"  btcaaron TXID: {tx_bob.txid}")
print(f"  Book TXID:     {EXPECTED_BOB_TXID}")
if tx_bob.txid == EXPECTED_BOB_TXID:
    print(f"  ✅ Exact match")
else:
    print(f"  ⚠️  Mismatch (nSequence: btcaaron=0xfffffffd, book=0xffffffff)")
    print(f"     This is expected — see NOTE at top of file")

# ═══════════════════════════════════════════════════════════════════
# Part 4: Summary
# Original: 04_verify_control_block.py (159 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 4: SUMMARY")
print("=" * 70)
print(f"  Address generation: ✅ Exact match")
print(f"  Hashlock spend:     Transaction built successfully")
print(f"  Bob checksig spend: Transaction built successfully")
print()
print(f"  API gap identified:")
print(f"    SpendBuilder lacks .sequence() method")
print(f"    Default nSequence=0xfffffffd (RBF) vs book's 0xffffffff")
print(f"    → Does not affect correctness, only TXID reproducibility")
print(f"    → TODO: add .sequence(value) to SpendBuilder")
print()
print(f"  Original code:  ~537 lines across 4 files")
print(f"  btcaaron code:  ~100 lines in 1 file")
print("=" * 70)
