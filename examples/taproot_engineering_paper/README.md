# Taproot Script-Path Engineering — paper reproduction package

Reproduction code for the paper **"Engineering Taproot Script-Path Spending: Design
Constraints, Security Pitfalls, and Reproducible Transaction Analysis"** (A. Zhang).

Everything here uses **public data only** — no private keys are included or required.

## Quick check (reviewers start here)

```bash
pip install coincurve
python3 verify.py
```

`verify.py` performs the exact check a Taproot verifier performs: it reconstructs the
output key *Q* for the §6.3 four-leaf address from the **published Script-1 control
block** (Merkle proof) and confirms it matches the address — using only the public
internal key, the script bytes, and the control block printed in the paper:

```
reconstructed address : tb1pf5rhd89h6hpgcf9eah2xxp4wnn9qzadlp56yj2vck8uu86erre4qg9vcse
published address     : tb1pf5rhd89h6hpgcf9eah2xxp4wnn9qzadlp56yj2vck8uu86erre4qg9vcse
PASS
```

## Files

| File | What it is |
|------|------------|
| `verify.py` | Standalone *Q*-from-control-block verifier (deps: `coincurve` only). |
| `four_leaf_lib.py` | Reference construction + all five spend builders (key/hash/multisig/CSV/sig) using **python-bitcoin-utils**. This is the code path that produced the on-chain TXIDs. |
| `two_leaf_lib.py` | The §6.2 two-leaf construction (hashlock + P2PK), reusing `four_leaf_lib`. |
| `four_leaf_btcaaron.py` | The same four-leaf experiment via **btcaaron's** declarative `TapTree`/`SpendBuilder` API — verified to produce the identical address and byte-identical hashlock spend. |
| `btcaaron_equivalence.md` | Record of the btcaaron ⇄ python-bitcoin-utils equivalence check. |
| `onchain_verification.md` | Record of all 10 TXIDs confirmed on local mainnet/signet full nodes (incl. the M2 `helloworld` witness). |

Deps for the construction libs: `python-bitcoin-utils>=0.7.3`, and `btcaaron` for the
declarative variant. The `four_leaf_lib` spend builders take keys as WIF arguments; no
keys are committed here.

## On-chain transactions (Appendix A of the paper)

Signet clean demonstrations (§6.2–6.3):

| ID | Role | TXID |
|----|------|------|
| S1 | two-leaf hashlock | [9d3d6d3b…cd7643](https://mempool.space/signet/tx/9d3d6d3bc97dc89af167703f4160095462f06d76f888b0a4891b94dfb6cd7643) |
| S2 | two-leaf P2PK | [7d7d064c…cce508](https://mempool.space/signet/tx/7d7d064cc4fcb7aa8148dfdfcbb6cbeb2e983c796de3a866481de92086cce508) |
| S3 | 4-leaf hashlock | [35d14e2f…2abf4b](https://mempool.space/signet/tx/35d14e2f7573403eae6e091177a2412e075e9c8c3742b0e1d90a3a22c72abf4b) |
| S4 | 4-leaf multisig | [c1b7f11a…373604](https://mempool.space/signet/tx/c1b7f11a4d751a3df9051e63a149309ba4a4743a4427437a0a00c12993373604) |
| S5 | 4-leaf CSV | [a69cd325…1c4fc48a](https://mempool.space/signet/tx/a69cd32512f5ac8f996f51d62ae4d10146049d5c647ac218ca0c981b1c4fc48a) |
| S6 | 4-leaf P2PK | [a5e38453…173d8c8](https://mempool.space/signet/tx/a5e38453b3b11f526dca3c2936bf0bb994cb8b7db5a01235e4f058eae173d8c8) |
| S7 | 4-leaf key path | [643a8f2b…dd977ba](https://mempool.space/signet/tx/643a8f2bc04c15cbfc8f9dc2fc4ea823ee28c90105ada96b606894c6fdd977ba) |

Mainnet live exploitation (§6.4 — the adversary's spends):

| ID | Role | TXID |
|----|------|------|
| M1 | hashlock front-run | [9fc1923c…4332dc363](https://mempool.space/tx/9fc1923c513cdf5a620ef88f61dbc3997e697cad0381b6f6c28827e4332dc363) |
| M2 | CSV-intended UTXO stolen via hashlock leaf (witness = `helloworld` + script + cb) | [4986e0ad…2c8966c1](https://mempool.space/tx/4986e0ad13e6b59193243cf44b7c20facde3350e22bdb4e3e54f0fad2c8966c1) |
| M3 | two-leaf hashlock UTXO stolen | [16c1b282…8a44a0f2](https://mempool.space/tx/16c1b282bf3325bdf765ede0e2c0cf91a1ffc3338531ecc761f9ed278a44a0f2) |
