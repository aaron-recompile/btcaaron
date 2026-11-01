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

## Third variant: TEMPLATEHASH + CSFS + INTERNALKEY (BIP 446 / 448)

[`th_csfs_ik_eltoo.py`](th_csfs_ik_eltoo.py) runs the same scenario with the opcode set Bitcoin Inquisition 29.4 activated on signet (TEMPLATEHASH active since block 314928), following the scripts in `instagibbs/bolts@2026-01-eltoo_th`:

```
EXPR_UPDATE(0)   = OP_TEMPLATEHASH OP_INTERNALKEY OP_CHECKSIGFROMSTACK                    3 B
EXPR_UPDATE(n>0) = ... OP_VERIFY <500000000+n> OP_CHECKLOCKTIMEVERIFY                     10 B
EXPR_SETTLE(n)   = OP_TEMPLATEHASH <template_hash(settle_n)> OP_EQUAL                     35 B
```

The update signature is over the BIP 446 template hash (no prevouts), so it rebinds to whichever older state is on chain; the update witness is 143 B regardless of state count. The template hash itself is in [`btcaaron/templatehash.py`](../../btcaaron/templatehash.py).

Reference run (Inquisition 29.4 signet, October 2026): stale state U1 published, then U3 (signed before any state output existed) rebinds onto it, skipping state 2.

| Phase | TxID |
|-------|------|
| Fund     | [`1163d3d5…9c259124`](https://mempool.space/signet/tx/1163d3d5ae78069dd41ad951de47460358db689b3b5d6b951dbb57399c259124) |
| U1 (stale) | [`22c0c67b…02188692`](https://mempool.space/signet/tx/22c0c67b33f6620fe9165dca835408de91f4dd873018ab1c06a26a2f02188692) |
| U3 rebinds onto S1 | [`4a11cfca…fdea15007`](https://mempool.space/signet/tx/4a11cfca7e35564f932ee30a66dec9f9bbd95cdbc8ad8b34190b4c8fdea15007) |
| Settle 3 | [`e7476180…6e8001568`](https://mempool.space/signet/tx/e7476180b2f784ce81c859c6a9d48a0f72c0e72937ac1cd37e183ec6e8001568) |

PoC deviations from the BOLT draft: single key K (no MuSig2), nVersion 2 with no P2A / OP_RETURN outputs, no HTLCs.

## Fourth variant: ANYPREVOUTANYSCRIPT + CLTV + CTV (BIP 118 / 119)

[`apoas_ctv_eltoo.py`](apoas_ctv_eltoo.py) runs the same stale-state override with the original eltoo construction: an APOAS (`0xc1`) signature plus a CLTV state number, settled by CTV.

```
UPDATE(0)   = OP_1 OP_CHECKSIG                                                  2 B
UPDATE(n>0) = <500000000+n> OP_CHECKLOCKTIMEVERIFY OP_DROP OP_1 OP_CHECKSIG     9 B
SETTLE(n)   = <ctv_hash(settle_n)> OP_CHECKTEMPLATEVERIFY                       34 B
```

APOAS commits to none of the outpoint, spent amount, spent scriptPubKey or tapleaf, so the update signature rebinds to any older state. The update witness is 143 B (65 B sig + 9 B leaf + 65 B control block), the same as the TEMPLATEHASH variant: the APO signature carries one extra sighash byte, the TEMPLATEHASH leaf one extra script byte.

Reference run (Inquisition signet, November 2026): U1–U3 signed before funding; stale U1 published, then U3 overrides it, skipping state 2. Mempool checks: wrong CLTV state number and early settlement are rejected, U2 rebinds onto S1, and a settlement with swapped amounts fails CTV.

| Phase | TxID |
|-------|------|
| Fund     | [`353dd22a…3c92ae0`](https://mempool.space/signet/tx/353dd22a1b506d97b00efd80a73b944e888dd2d0386a7ceaadb67f8eb3c92ae0) |
| U1 (stale) | [`c47fb794…f0c5807`](https://mempool.space/signet/tx/c47fb79420d977eacbcf8087a14513fedd02b1f35e922b908cce0e5dcf0c5807) |
| U3 overrides S1 | [`68a7405e…a5336d28`](https://mempool.space/signet/tx/68a7405e5541a169793d4b88b07b564618be5ab0c28d86b71bda5e0fa5336d28) |
| Settle 3 | [`41198470…fe2a4788`](https://mempool.space/signet/tx/411984708c58071787f29c93816a82dc25a846017a272c3b77b5069afe2a4788) |

## Files

| File | Role |
|------|------|
| `csfs_ladder_ctv.py` | Main: `--fund` / `--delegate` / `--spend` |
| `th_csfs_ik_eltoo.py` | TEMPLATEHASH + CSFS + IK variant: `--setup` / `--fund` / `--stale` / `--rebind` / `--settle` and mempool checks |
| `apoas_ctv_eltoo.py` | APOAS + CLTV + CTV variant: same phases, `--status` prints sizes |
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

## Key-free verification

`python examples/verify_onchain.py` checks, with no keys and no node, that the transactions of both
eltoo variants in this folder (CSFS ladder: `92efc475...`, `b96324da...`; TEMPLATEHASH + CSFS + IK: the
four TXIDs above) are confirmed on signet and that their raw bytes hash to the cited TXIDs.
