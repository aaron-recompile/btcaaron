#!/usr/bin/env python3
"""
Chapter 8: Four-Leaf Taproot Script Tree (btcaaron version)

Covers the SAME content as 7 original files in mastering-taproot/code/chapter08/:
  01_create_four_leaf_taproot.py   → Part 1: Build Tree
  02_hashlock_path_spending.py     → Part 2: Hashlock spend
  03_multisig_path_spending.py     → Part 3: Multisig spend
  04_csv_timelock_path_spending.py → Part 4: CSV Timelock spend
  05_simple_sig_path_spending.py   → Part 5: Checksig spend
  06_key_path_spending.py          → Part 6: Key-path spend
  07_verify_control_blocks.py      → Part 7: Verify all TXIDs

Original code: ~900 lines across 7 files
btcaaron version: ~140 lines in 1 file

Run: python examples/ch08_four_leaf_tree.py
"""

from btcaaron import Key, TapTree

# ═══════════════════════════════════════════════════════════════════
# Keys — same WIFs used throughout the book
# ═══════════════════════════════════════════════════════════════════

alice = Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob   = Key.from_wif("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")

# ═══════════════════════════════════════════════════════════════════
# Part 1: Build the 4-leaf Taproot tree
# Original: 01_create_four_leaf_taproot.py (141 lines)
# ═══════════════════════════════════════════════════════════════════

program = (TapTree(internal_key=alice)
    .hashlock("helloworld", label="hash")            # Script 0: SHA256 hash lock
    .multisig(2, [alice, bob], label="2of2")          # Script 1: 2-of-2 CHECKSIGADD
    .timelock(blocks=2, then=bob, label="csv")        # Script 2: CSV relative timelock
    .checksig(bob, label="bob")                       # Script 3: simple signature
).build()

print("=" * 70)
print("PART 1: FOUR-LEAF TAPROOT TREE CONSTRUCTION")
print("=" * 70)
print(f"  Address:  {program.address}")
print(f"  Leaves:   {program.leaves}")
print(f"  Visualization:")
print(program.visualize())

# Verify address matches Chapter 8's expected value
assert program.address == "tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q"
print("  ✅ Address matches Chapter 8")

# ═══════════════════════════════════════════════════════════════════
# Part 2: Hashlock script-path spending
# Original: 02_hashlock_path_spending.py (117 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 2: HASHLOCK SCRIPT-PATH SPENDING")
print("=" * 70)

tx_hash = (program.spend("hash")
    .from_utxo("245563c5aa4c6d32fc34eed2f182b5ed76892d13370f067dc56f34616b66c468", 0, sats=1200)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 666)
    .unlock(preimage="helloworld")
    .build())

print(f"  TXID: {tx_hash.txid}")
EXPECTED_HASH = "1ba4835fca1c94e7eb0016ce37c6de2545d07d84a97436f8db999f33a6fd6845"
match = tx_hash.txid == EXPECTED_HASH
print(f"  Expected: {EXPECTED_HASH}")
print(f"  Match: {'✅' if match else '❌'}")

# ═══════════════════════════════════════════════════════════════════
# Part 3: 2-of-2 Multisig script-path spending
# Original: 03_multisig_path_spending.py (142 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 3: MULTISIG (2-OF-2) SCRIPT-PATH SPENDING")
print("=" * 70)

tx_multi = (program.spend("2of2")
    .from_utxo("1ed5a3e97a6d3bc0493acc2aac15011cd99000b52e932724766c3d277d76daac", 0, sats=1400)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 668)
    .sign(alice, bob)
    .build())

print(f"  TXID: {tx_multi.txid}")
EXPECTED_MULTI = "1951a3be0f05df377b1789223f6da66ed39c781aaf39ace0bf98c3beb7e604a1"
match = tx_multi.txid == EXPECTED_MULTI
print(f"  Expected: {EXPECTED_MULTI}")
print(f"  Match: {'✅' if match else '❌'}")

# ═══════════════════════════════════════════════════════════════════
# Part 4: CSV Timelock script-path spending
# Original: 04_csv_timelock_path_spending.py (131 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 4: CSV TIMELOCK SCRIPT-PATH SPENDING")
print("=" * 70)

tx_csv = (program.spend("csv")
    .from_utxo("9a2bff4161411f25675c730777c7b4f5b2837e19898500628f2010c1610ac345", 0, sats=1600)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 800)
    .sign(bob)
    .build())

print(f"  TXID: {tx_csv.txid}")
EXPECTED_CSV = "98361ab2c19aa0063f7572cfd0f66cb890b403d2dd12029426613b40d17f41ee"
match = tx_csv.txid == EXPECTED_CSV
print(f"  Expected: {EXPECTED_CSV}")
print(f"  Match: {'✅' if match else '❌'}")

# ═══════════════════════════════════════════════════════════════════
# Part 5: Simple Signature (checksig) script-path spending
# Original: 05_simple_sig_path_spending.py (128 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 5: SIMPLE SIGNATURE (CHECKSIG) SCRIPT-PATH SPENDING")
print("=" * 70)

tx_sig = (program.spend("bob")
    .from_utxo("632743eb43aa68fb1c486bff48e8b27c436ac1f0d674265431ba8c1598e2aeea", 0, sats=1800)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 866)
    .sign(bob)
    .build())

print(f"  TXID: {tx_sig.txid}")
EXPECTED_SIG = "1af46d4c71e121783c3c7195f4b45025a1f38b73fc8898d2546fc33b4c6c71b9"
match = tx_sig.txid == EXPECTED_SIG
print(f"  Expected: {EXPECTED_SIG}")
print(f"  Match: {'✅' if match else '❌'}")

# ═══════════════════════════════════════════════════════════════════
# Part 6: Key-path spending (maximum privacy)
# Original: 06_key_path_spending.py (117 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 6: KEY-PATH SPENDING (MAXIMUM PRIVACY)")
print("=" * 70)

tx_key = (program.keypath()
    .from_utxo("42a9796a91cf971093b35685db9cb1a164fb5402aa7e2541ea7693acc1923059", 0, sats=2000)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 888)
    .sign(alice)
    .build())

print(f"  TXID: {tx_key.txid}")
EXPECTED_KEY = "1e518aa540bc770df549ec9836d89783ca19fc79b84e7407a882cbe9e95600da"
match = tx_key.txid == EXPECTED_KEY
print(f"  Expected: {EXPECTED_KEY}")
print(f"  Match: {'✅' if match else '❌'}")

# ═══════════════════════════════════════════════════════════════════
# Part 7: Summary — verify all 5 TXIDs
# Original: 07_verify_control_blocks.py (175 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 7: VERIFICATION SUMMARY")
print("=" * 70)

results = [
    ("Hashlock",   tx_hash.txid,  EXPECTED_HASH),
    ("Multisig",   tx_multi.txid, EXPECTED_MULTI),
    ("CSV Lock",   tx_csv.txid,   EXPECTED_CSV),
    ("Checksig",   tx_sig.txid,   EXPECTED_SIG),
    ("Key Path",   tx_key.txid,   EXPECTED_KEY),
]

all_pass = True
for name, actual, expected in results:
    ok = actual == expected
    all_pass = all_pass and ok
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name:12s}  {actual[:16]}...")

print(f"\n  All 5 paths: {'ALL PASS' if all_pass else 'SOME FAILED'}")
print(f"\n  Original code:  ~900 lines across 7 files")
print(f"  btcaaron code:  {__import__('inspect').getsourcefile(type(program))} (this file: ~140 lines)")
print("=" * 70)
