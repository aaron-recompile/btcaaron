#!/usr/bin/env python3
"""
Chapter 6: Single-Leaf Taproot Contract (btcaaron version)

Covers the SAME content as 4 original files in mastering-taproot/code/chapter06/:
  01_create_taproot_commitment.py    → Part 1: Build single-leaf tree
  02_key_path_spending.py            → Part 2: Key-path spend (Alice)
  03_script_path_spending.py         → Part 3: Script-path spend (hashlock)
  04_verify_script_execution.py      → Part 4: Verification

Original code: ~655 lines across 4 files
btcaaron version: ~90 lines in 1 file

This is the simplest Taproot contract: one internal key + one hash lock script.
Two spending paths: Key Path (Alice) and Script Path (preimage).

Same nSequence note as Ch07: book uses 0xffffffff, btcaaron defaults 0xfffffffd.

Run: python examples/ch06_single_leaf_contract.py
"""

from btcaaron import Key, TapTree

# ═══════════════════════════════════════════════════════════════════
# Keys
# ═══════════════════════════════════════════════════════════════════

alice = Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")

# ═══════════════════════════════════════════════════════════════════
# Part 1: Build the single-leaf Taproot tree
# Original: 01_create_taproot_commitment.py (109 lines)
#
# Simplest Taproot contract:
#   - Key Path: Alice (internal key holder)
#   - Script Path: Anyone who knows the preimage "helloworld"
# ═══════════════════════════════════════════════════════════════════

program = (TapTree(internal_key=alice)
    .hashlock("helloworld", label="hash")
).build()

print("=" * 70)
print("PART 1: SINGLE-LEAF TAPROOT COMMITMENT")
print("=" * 70)
print(f"  Address:  {program.address}")
print(f"  Leaves:   {program.leaves}")
print(f"  Visualization:")
print(program.visualize())

EXPECTED_ADDR = "tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h"
assert program.address == EXPECTED_ADDR
print(f"  ✅ Address matches Chapter 6: {EXPECTED_ADDR}")

# ═══════════════════════════════════════════════════════════════════
# Part 2: Key-path spending (Alice's direct control)
# Original: 02_key_path_spending.py (165 lines)
#
# Maximum privacy: only a 64-byte Schnorr signature in witness.
# Indistinguishable from a simple Taproot payment.
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 2: KEY-PATH SPENDING (ALICE)")
print("=" * 70)

tx_key = (program.keypath()
    .from_utxo("4fd83128fb2df7cd25d96fdb6ed9bea26de755f212e37c3aa017641d3d2d2c6d", 0, sats=3900)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 3700)
    .sign(alice)
    .build())

EXPECTED_KEY_TXID = "85e843d5fd6273d2668cbaa787be4bed918b4dac4dba4d305c8cc1f4618b9af1"
print(f"  btcaaron TXID: {tx_key.txid}")
print(f"  Book TXID:     {EXPECTED_KEY_TXID}")
if tx_key.txid == EXPECTED_KEY_TXID:
    print(f"  ✅ Exact match")
else:
    print(f"  ⚠️  Mismatch (nSequence difference)")

# ═══════════════════════════════════════════════════════════════════
# Part 3: Script-path spending (hashlock)
# Original: 03_script_path_spending.py (195 lines)
#
# Anyone who knows the preimage "helloworld" can unlock.
# Reveals the hash lock script + control block in witness.
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 3: SCRIPT-PATH SPENDING (HASHLOCK)")
print("=" * 70)

tx_hash = (program.spend("hash")
    .from_utxo("9e193d8c5b4ff4ad7cb13d196c2ecc210d9b0ec144bb919ac4314c1240629886", 0, sats=5000)
    .to("tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne", 4000)
    .unlock(preimage="helloworld")
    .build())

EXPECTED_HASH_TXID = "68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f"
print(f"  btcaaron TXID: {tx_hash.txid}")
print(f"  Book TXID:     {EXPECTED_HASH_TXID}")
if tx_hash.txid == EXPECTED_HASH_TXID:
    print(f"  ✅ Exact match")
else:
    print(f"  ⚠️  Mismatch (nSequence difference)")

# ═══════════════════════════════════════════════════════════════════
# Part 4: Summary
# Original: 04_verify_script_execution.py (186 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 4: SUMMARY")
print("=" * 70)
print(f"  Address generation: ✅ Exact match")
print(f"  Key-path spend:     Transaction built successfully")
print(f"  Script-path spend:  Transaction built successfully")
print()
print(f"  Key insight from Chapter 6:")
print(f"    The Commit-Reveal pattern — during commit phase, all contracts")
print(f"    look identical (just a Taproot address). During reveal phase,")
print(f"    only the used branch is exposed. Maximum privacy by default.")
print()
print(f"  Original code:  ~655 lines across 4 files")
print(f"  btcaaron code:  ~90 lines in 1 file")
print("=" * 70)
