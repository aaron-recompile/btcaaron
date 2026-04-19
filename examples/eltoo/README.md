# Eltoo on Inquisition signet — CSFS ladder + CTV

A reproduction of an eltoo-style state chain using only **already-activated** Inquisition opcodes:

- **OP_CHECKSIGFROMSTACK** (BIP-348) — verifies a signature over arbitrary stack data.
- **OP_CHECKTEMPLATEVERIFY** (BIP-119) — enforces the spend transaction matches a precommitted output template.

Three rounds of state progression compress into **two on-chain transactions** (fund + settle). State progression is encoded as an off-chain **CSFS rekey ladder** (K → R₀ → R₁ → R₂); the terminal state's key signs a CTV template hash that enforces the 3-output payout on chain.

## Companion to the APO+CTV demo

This example is the second primitive set for the same eltoo scenario already
implemented in [`examples/braidpool/rca_eltoo_chain.py`](../braidpool/rca_eltoo_chain.py)
(APO + CTV, 6 transactions). Same Alice/Bob/Carol payout amounts, different opcodes:

| | APO + CTV (`braidpool/rca_eltoo_chain.py`) | CSFS + CTV (this example) |
|---|---|---|
| Opcodes | APO + CTV | CSFS + CTV |
| State mechanism | APO signature rebinding (1 tx per state) | CSFS ladder delegation (all states in 1 witness) |
| On-chain txs | 6 | 2 |
| Witness per spend | ~150B | 512B (carries full state history) |
| Settlement | CTV (3 outputs) | CTV (3 outputs) |

Both run on Inquisition signet today. They make different cost/structure tradeoffs but reach the same protocol-level outcome.

## Scenario

```
State 0: Alice 50,000  Bob 30,000  Carol 20,000  (initial)
State 1: Alice 45,000  Bob 35,000  Carol 20,000  (Alice pays Bob)
State 2: Alice 40,000  Bob 35,000  Carol 25,000  (Alice pays Carol)
```

## Tapscript (42 bytes)

```
<K_pub_32> OP_CHECKSIGFROMSTACK OP_VERIFY
           OP_CHECKSIGFROMSTACK OP_VERIFY
           OP_CHECKSIGFROMSTACK OP_VERIFY
           OP_CHECKSIGFROMSTACK OP_VERIFY
           OP_CHECKTEMPLATEVERIFY
```

4× CSFS (3 delegation hops + 1 settlement signing) + 1× CTV (output enforcement). No OP_CAT, no OP_DUP, no stack manipulation opcodes — duplication of intermediate keys is achieved by witness layout.

## Prerequisites

- **btcaaron** installed from this repo (`pip install -e .`).
- Inquisition signet **bitcoind** with `bitcoin-cli` available, wallet **`lab`** loaded.
- Environment:
  - **`CAT_DEMO_WIF`** — signet WIF for the channel root key K.
  - **`INQUISITION_DATADIR`** — path to the node datadir.
  - Optional: **`INQUISITION_RPC_PORT`**, **`BITCOIN_CLI`**.

`CAT_DEMO_WIF` and `INQUISITION_*` can be placed in a **`.env` file at the btcaaron repository root**; `load_local_env.py` reads it automatically.

## Run

From the **btcaaron repository root**:

```bash
# 1) Lock 101,000 sats to the ladder+CTV address
PYTHONPATH=. python3 examples/eltoo/csfs_ladder_ctv.py --fund

# 2) Build the off-chain delegation chain K → R₀ → R₁ → R₂ and the settlement signature
PYTHONPATH=. python3 examples/eltoo/csfs_ladder_ctv.py --delegate

# 3) Broadcast the spend: settles to Alice/Bob/Carol per State 2, CTV-enforced
PYTHONPATH=. python3 examples/eltoo/csfs_ladder_ctv.py --spend
```

Inspect on chain:

```bash
btcrun inq trace <txid>
```

## Reference on-chain run

Reproduced run on Inquisition signet (April 2026):

| Phase | TxID |
|-------|------|
| Fund  | [`92efc475…531fda34`](https://mempool.space/signet/tx/92efc47554d25d74d9f567594d37375d8c8a1a2ea6bd1864600d5a49531fda34?showDetails=true) |
| Spend | [`b96324da…238382de`](https://mempool.space/signet/tx/b96324da612950339f564fbc88fe1d5c5751070e57bf796d32ee7171238382de?showDetails=true) |

The spend transaction has 3 outputs (CTV-enforced): Alice 40,000 / Bob 35,000 / Carol 25,000, plus 1,000 sats fee.

## Files

| File | Role |
|------|------|
| `csfs_ladder_ctv.py` | Main: `--fund` / `--delegate` / `--spend` |
| `opcodes.py` | Inquisition opcode constants (CSFS, CTV, etc.) and minimal `build_script` / `push_bytes` helpers |
| `eltoo_config.py` | `bitcoin-cli` RPC wrappers (mirrors `examples/braidpool/braidpool_config.py`) |
| `load_local_env.py` | Optional repo-root `.env` loader |

## Construction notes

The rekey/ladder pattern was sketched conceptually by Jeremy Rubin in [a December 2024 blog post](https://rubin.io/bitcoin/2024/12/02/csfs-ctv-rekey-symmetry/). This example is an engineering implementation choosing:

- **Witness duplication** (each intermediate key R_i appears twice in the witness) instead of `DUP TOALT DUP TOALT` ALTSTACK shuffling. Script stays flat at 42 bytes.
- **Deterministic SHA256 derivation** `R_i = SHA256(K_secret || "state_i")` instead of BIP32 path derivation. Either works; the simpler form reduces dependency surface.
- **CTV-hash interlock** via duplicated witness slot (`[2]` consumed by CSFS #4 as the message R₂ signs; `[0]` survives at the bottom for the final CTV opcode to check against the spending transaction's outputs).

This is a **feasibility demonstration on already-activated opcodes**, not a production LN-Symmetry channel. Witness size grows O(N) with state count (~160B per additional hop); the maximum hop count is hardcoded at funding time. For high-throughput LN channels, O(1)-witness alternatives (PAIRCOMMIT, OP_TXHASH) would be preferable — none are activated as of this writing.

Long-form analysis lives outside this repo; this folder is **runnable code + this README only**.
