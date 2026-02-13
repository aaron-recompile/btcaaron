#!/usr/bin/env python3
"""
Chapter 9: PSBT Multisig Flow (Taproot)

Demonstrates btcaaron's PSBT v0 flow for Taproot 2-of-2 multisig:
  1. Build unsigned transaction as PSBT
  2. Sign with Alice, then Bob (order doesn't matter)
  3. Finalize and extract signed transaction

Can also serialize to base64 for transport (e.g. between signers).

Run: PYTHONPATH=. python examples/ch09_psbt_multisig.py
"""

from btcaaron import Key, TapTree, Psbt

# ═══════════════════════════════════════════════════════════════════
# Keys (testnet)
# ═══════════════════════════════════════════════════════════════════

alice = Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob = Key.from_wif("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")

# ═══════════════════════════════════════════════════════════════════
# Build 2-of-2 multisig Taproot program
# ═══════════════════════════════════════════════════════════════════

program = (TapTree(internal_key=alice)
    .hashlock("helloworld", label="hash")
    .multisig(2, [alice, bob], label="2of2")
).build()

print("=" * 60)
print("PSBT MULTISIG FLOW (Taproot 2-of-2)")
print("=" * 60)
print(f"  Address: {program.address}")
print(f"  Leaf:    2of2 (requires Alice + Bob signatures)")
print()

# ═══════════════════════════════════════════════════════════════════
# Part 1: Direct PSBT flow (same process)
# ═══════════════════════════════════════════════════════════════════

print("PART 1: Direct PSBT flow")
print("-" * 40)

psbt = (program.spend("2of2")
    .from_utxo("b" * 64, 0, sats=1000)
    .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 500)
    .to_psbt())

psbt.sign_with(alice, 0)
psbt.sign_with(bob, 0)
psbt.finalize()
tx = psbt.extract_transaction()

txid = tx.get_txid()
print(f"  TXID: {txid}")
print(f"  Fee:  500 sats")
print(f"  ✅ Transaction built successfully")
print()

# ═══════════════════════════════════════════════════════════════════
# Part 2: base64 roundtrip (simulate handoff between signers)
# ═══════════════════════════════════════════════════════════════════

print("PART 2: base64 roundtrip (Alice → serialize → Bob deserializes & signs)")
print("-" * 40)

psbt_a = (program.spend("2of2")
    .from_utxo("c" * 64, 0, sats=800)
    .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", 300)
    .to_psbt())

# Alice signs, then serializes for Bob
psbt_a.sign_with(alice, 0)
b64 = psbt_a.to_base64()

# Bob receives the base64 string, deserializes, adds his sig, finalizes
psbt_b = Psbt.from_base64(b64)
psbt_b.sign_with(bob, 0)
psbt_b.finalize()
tx2 = psbt_b.extract_transaction()

txid2 = tx2.get_txid()
print(f"  TXID: {txid2}")
print(f"  Fee:  500 sats")
print(f"  ✅ Roundtrip successful")
print()

# ═══════════════════════════════════════════════════════════════════
# Part 3: Verify with real testnet TXID (VERIFIED_TXS)
# ═══════════════════════════════════════════════════════════════════

print("PART 3: Verified testnet TXID reproduction")
print("-" * 40)

VERIFIED_MULTISIG = {
    "txid": "93c0e6ab682e2e5d088cc8175aaddc5d62f4b1de2b234dad566085a97b60581d",
    "input_txid": "76906b969d65177c5d8af3103e683aa1c02abafa94368d6a6ae1fe78b8aa49dd",
    "input_vout": 0,
    "input_sats": 2888,
    "output_sats": 2388,
}

psbt_v = (program.spend("2of2")
    .from_utxo(VERIFIED_MULTISIG["input_txid"], VERIFIED_MULTISIG["input_vout"], sats=VERIFIED_MULTISIG["input_sats"])
    .to("tb1qr65sfajzw8f4rh8d593zm6wryxcukulygv2209", VERIFIED_MULTISIG["output_sats"])
    .to_psbt())
psbt_v.sign_with(alice, 0)
psbt_v.sign_with(bob, 0)
psbt_v.finalize()
tx_v = psbt_v.extract_transaction()

got = tx_v.get_txid()
expected = VERIFIED_MULTISIG["txid"]
print(f"  Expected: {expected}")
print(f"  Got:     {got}")
if got == expected:
    print(f"  ✅ Exact TXID match (mempool.space/testnet verified)")
else:
    print(f"  ⚠️  Mismatch")
print()
print("=" * 60)
