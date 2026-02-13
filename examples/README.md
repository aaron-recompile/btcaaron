# btcaaron Examples

These examples rewrite the code from [Mastering Taproot](https://github.com/aaron-recompile/mastering-taproot) using btcaaron's semantic API, demonstrating how the library simplifies Taproot engineering.

## Quick Start

```bash
# From the btcaaron root directory
PYTHONPATH=. python examples/ch08_four_leaf_tree.py
```

## Examples

| File | Book Chapter | Original | btcaaron | Reduction |
|------|-------------|----------|----------|-----------|
| [ch01_keys_and_addresses.py](ch01_keys_and_addresses.py) | Ch01: Keys & Addresses | ~200 lines / 5 files | ~80 lines / 1 file | 60% |
| [ch05_simple_taproot.py](ch05_simple_taproot.py) | Ch05: Simple Taproot | ~334 lines / 2 files | ~70 lines / 1 file | 79% |
| [ch06_single_leaf_contract.py](ch06_single_leaf_contract.py) | Ch06: Single-Leaf Contract | ~655 lines / 4 files | ~90 lines / 1 file | 86% |
| [ch07_dual_leaf_tree.py](ch07_dual_leaf_tree.py) | Ch07: Dual-Leaf Tree | ~537 lines / 4 files | ~100 lines / 1 file | 81% |
| [ch08_four_leaf_tree.py](ch08_four_leaf_tree.py) | Ch08: Four-Leaf Tree | ~900 lines / 7 files | ~140 lines / 1 file | 84% |
| [ch09_psbt_multisig.py](ch09_psbt_multisig.py) | Ch09: PSBT Multisig | — | ~100 lines | New |

**Total: ~2,626 lines / 22 files → ~580 lines / 6 files**

## TXID Verification Results

| Chapter | Address Match | TXID Match | Notes |
|---------|:------------:|:----------:|-------|
| Ch05 | ✅ | N/A | No on-chain tx to verify |
| Ch06 | ✅ | ⚠️ | nSequence difference (0xfffffffd vs 0xffffffff) |
| Ch07 | ✅ | ⚠️ | nSequence difference (same as Ch06) |
| Ch08 | ✅ | ✅ 5/5 | All 5 spending paths match exactly |

Ch08 achieves exact TXID match because the original code also uses `nSequence=0xfffffffd`. Ch06/07 use `0xffffffff`.

## API Gaps Identified

These gaps were discovered by running the book examples through btcaaron:

| Gap | Severity | Status |
|-----|----------|--------|
| `Key.generate()` raises NotImplementedError | Blocker | TODO |
| `SpendBuilder` lacks `.sequence()` method | Medium | TODO — causes TXID mismatch for Ch06/07 |
| No Legacy/SegWit address generation | By Design | btcaaron is Taproot-focused |

## How These Examples Were Created

Each example follows the same pattern:

1. Read the original chapter code (bitcoin-utils, manual scripts)
2. Rewrite using btcaaron's semantic API (`TapTree`, `SpendBuilder`)
3. Run and verify address/TXID matches
4. Document any API gaps discovered

The goal is not to replace the book — the book teaches the underlying principles. These examples show what the same operations look like when the complexity is abstracted into a library.
