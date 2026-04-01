# Braidpool covenant demos (Inquisition signet)

Minimal examples using **btcaaron** on a **Bitcoin Inquisition** signet node: one **TapTree** with **CTV** (UHPO-shaped settlement), **BIP118 / APO** (update path), and **CSV** (timeout path). These are **not** a full Braidpool protocol implementation.

## Prerequisites

- **btcaaron** install from this repo (`pip install -e .` or your usual workflow).
- Inquisition **signet** `bitcoind` with `bitcoin-cli`, wallet **`lab`** loaded.
- Environment:
  - **`CAT_DEMO_WIF`** — private key for the demo internal key (Taproot scripts).
  - **`INQUISITION_DATADIR`** — path to the node datadir.
  - Optional: **`INQUISITION_RPC_PORT`**, **`BITCOIN_CLI`**.

You can put `CAT_DEMO_WIF` and `INQUISITION_*` in a **`.env` file at the btcaaron repository root** (loaded automatically by `load_local_env.py`).

## Scripts (run from repository root)

```bash
# Three-leaf tree: fund once, then spend one path (ctv | apo | csv)
PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --fund
PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --spend ctv
# Optional: APO-only double-fund + signature reuse (BIP118) demo
PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --fund-apo-rebind
PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --spend-apo-rebind

# Multi-hop: RCA v1 → v2 → v3 via APO, then CTV settlement (one command)
PYTHONPATH=. python3 examples/braidpool/rca_eltoo_chain.py --run
```

Inspect transactions locally (e.g. with **btcrun**):

```bash
btcrun inq trace <txid>
```

## Files

| File | Role |
|------|------|
| `rca_taptree_smoke.py` | Single-tree smoke: `--fund`, `--spend ctv\|apo\|csv`, optional `--fund-apo-rebind` / `--spend-apo-rebind` |
| `rca_eltoo_chain.py` | Full `--run` chain: fund → APO → APO → CTV settle |
| `braidpool_config.py` | `bitcoin-cli` RPC to Inquisition |
| `template_common.py` | Fund/broadcast/UTXO helpers |
| `load_local_env.py` | Optional root `.env` loading |

Long-form analysis write-ups stay outside this repo; this folder is **runnable code + this README only**.
