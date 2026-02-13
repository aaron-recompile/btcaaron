#!/usr/bin/env python3
"""
Chapter 5: Simple Taproot Transaction (btcaaron version)

Covers the SAME content as 2 original files in mastering-taproot/code/chapter05/:
  01_demonstrate_key_tweaking.py            → Part 1: Key tweaking (abstracted)
  02_create_simple_taproot_transaction.py   → Part 2: Key-path-only transaction

Original code: ~334 lines across 2 files
btcaaron version: ~70 lines in 1 file

Key insight: btcaaron abstracts away the key tweaking math entirely.
You don't need to understand tagged hashes, tweak formulas, or curve math.
Just declare your intent, and the library handles the rest.

For the underlying math, see Chapter 5 of the book.

Run: python examples/ch05_simple_taproot.py
"""

from btcaaron import Key, TapTree

# ═══════════════════════════════════════════════════════════════════
# Part 1: Key Tweaking (abstracted by btcaaron)
# Original: 01_demonstrate_key_tweaking.py (162 lines)
#
# The original file manually demonstrates:
#   - tagged_hash("TapTweak", internal_pubkey || merkle_root)
#   - d' = d + t (mod n)
#   - P' = P + t*G
#   - Mathematical verification
#
# btcaaron does all of this internally when you call .build().
# You never see the tweak, the curve math, or the tagged hash.
# ═══════════════════════════════════════════════════════════════════

sender = Key.from_wif("cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT")

# Key-path-only: no scripts, just the internal key
program = TapTree(internal_key=sender).build()

print("=" * 70)
print("PART 1: KEY-PATH-ONLY TAPROOT ADDRESS")
print("=" * 70)
print(f"  Internal key (x-only): {sender.xonly}")
print(f"  Taproot address:       {program.address}")
print(f"  Leaves: {program.leaves} (empty — key-path only)")
print(f"  {program.visualize()}")
print()
print(f"  What btcaaron did internally (you don't need to know):")
print(f"    1. Extract x-only pubkey from internal key")
print(f"    2. Compute tweak: t = HashTapTweak(x-only pubkey)")
print(f"    3. Compute output key: P' = P + t*G")
print(f"    4. Encode as bech32m address (tb1p...)")
print(f"  See Chapter 5 of the book for the full math.")

# ═══════════════════════════════════════════════════════════════════
# Part 2: Simple Taproot-to-Taproot transaction
# Original: 02_create_simple_taproot_transaction.py (172 lines)
#
# A key-path spend: the simplest possible Taproot transaction.
# Witness = [64-byte Schnorr signature] — nothing else.
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 2: SIMPLE TAPROOT TRANSACTION (KEY-PATH)")
print("=" * 70)

tx = (program.keypath()
    .from_utxo("b0f49d2f30f80678c6053af09f0611420aacf20105598330cb3f0ccb8ac7d7f0", 0, sats=29200)
    .to("tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h", 29000)
    .sign(sender)
    .build())

print(f"  From:   {program.address}")
print(f"  To:     tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h")
print(f"  Amount: 29,000 sats (fee: 200 sats)")
print(f"  TXID:   {tx.txid}")
print()
print(f"  Witness: 64-byte Schnorr signature (no public key, no script)")
print(f"  This is indistinguishable from any other Taproot payment.")

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("SUMMARY: THE POWER OF ABSTRACTION")
print("=" * 70)
print(f"  Original Ch05 code:")
print(f"    01_demonstrate_key_tweaking.py     162 lines (manual math)")
print(f"    02_create_simple_taproot_transaction.py  172 lines")
print(f"    Total: ~334 lines across 2 files")
print()
print(f"  btcaaron version:")
print(f"    Key-path-only address:  TapTree(internal_key=sender).build()")
print(f"    Send transaction:       program.keypath().from_utxo(...).to(...).sign(...).build()")
print(f"    Total: ~70 lines in 1 file")
print()
print(f"  The key tweaking math is essential to understand (read the book).")
print(f"  But you shouldn't have to write it every time you use Taproot.")
print("=" * 70)
