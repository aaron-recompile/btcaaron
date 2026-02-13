#!/usr/bin/env python3
"""
Chapter 1: Keys and Addresses (btcaaron version)

Covers the SAME content as 5 original files in mastering-taproot/code/chapter01/:
  01_generate_private_key.py    → Part 1: Key generation
  02_generate_public_key.py     → Part 2: Public key derivation
  03_taproot_xonly_pubkey.py    → Part 3: X-only pubkey
  04_generate_addresses.py      → Part 4: Address generation
  05_verify_addresses.py        → Part 5: Address verification

Original code: ~200 lines across 5 files
btcaaron version: ~80 lines in 1 file

Note: btcaaron is Taproot-focused (no Legacy/SegWit address generation)

Run: python examples/ch01_keys_and_addresses.py
"""

from btcaaron import Key, TapTree

# ═══════════════════════════════════════════════════════════════════
# Part 1: Key creation
# Original: 01_generate_private_key.py (33 lines)
#
# Original: priv = PrivateKey()  ← random generation
# btcaaron: Key.generate()       ← same semantics
# ═══════════════════════════════════════════════════════════════════

print("=" * 70)
print("PART 1: KEY CREATION")
print("=" * 70)

# Generate a new random key
alice = Key.generate()
print(f"  Generated key WIF: {alice.wif}")

# ═══════════════════════════════════════════════════════════════════
# Part 2 & 3: Public key derivation + x-only
# Original: 02_generate_public_key.py + 03_taproot_xonly_pubkey.py (~65 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 2: PUBLIC KEY DERIVATION")
print("=" * 70)

print(f"  Compressed pubkey (33 bytes): {alice.pubkey}")
print(f"  X-only pubkey (32 bytes):     {alice.xonly}")
print()
print(f"  X-only = compressed pubkey minus the 02/03 prefix byte")
print(f"  Verify: {alice.pubkey[2:]} == {alice.xonly}")
assert alice.pubkey[2:] == alice.xonly
print(f"  ✅ Match")

# ═══════════════════════════════════════════════════════════════════
# Part 4: Taproot address generation
# Original: 04_generate_addresses.py (48 lines)
#
# Original generates: P2PKH, P2WPKH, P2SH-P2WPKH, P2TR
# btcaaron only generates: P2TR (Taproot-focused by design)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 3: TAPROOT ADDRESS GENERATION")
print("=" * 70)

program = TapTree(internal_key=alice).build()
print(f"  Taproot (P2TR):  {program.address}")
print()
print(f"  btcaaron is Taproot-focused by design.")
print(f"  For Legacy/SegWit addresses, use bitcoin-utils directly:")
print(f"    legacy  = pub.get_address()          # P2PKH: 1... or m/n...")
print(f"    segwit  = pub.get_segwit_address()   # P2WPKH: bc1q... or tb1q...")
print(f"    taproot = pub.get_taproot_address()   # P2TR: bc1p... or tb1p...")

# ═══════════════════════════════════════════════════════════════════
# Part 5: Key format summary
# Original: 05_verify_addresses.py (~40 lines)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 4: KEY FORMAT SUMMARY")
print("=" * 70)
print(f"  {'Format':<25} {'Length':<12} {'Value'}")
print(f"  {'─' * 25} {'─' * 12} {'─' * 40}")
print(f"  {'WIF (private)':<25} {'52 chars':<12} {alice.wif[:20]}...")
print(f"  {'Compressed pubkey':<25} {'33 bytes':<12} {alice.pubkey[:20]}...")
print(f"  {'X-only pubkey':<25} {'32 bytes':<12} {alice.xonly[:20]}...")
print(f"  {'Taproot address':<25} {'62 chars':<12} {program.address[:20]}...")

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  Key.generate()       → Random key generation")
print(f"  Key.from_wif()       → Import from WIF")
print(f"  Legacy/SegWit addrs  → Not in scope (btcaaron is Taproot-focused)")
print()
print(f"  Original code:  ~200 lines across 5 files")
print(f"  btcaaron code:  ~70 lines in 1 file")
print("=" * 70)
