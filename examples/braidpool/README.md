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

## On-chain record (Inquisition signet)

Produced with `rca_eltoo_chain.py --run` and the `--fund-apo-rebind` / `--spend-apo-rebind` steps of `rca_taptree_smoke.py`.

| Step | TXID |
|------|------|
| Fund -> state v1 | [`386dbb6a...9c41`](https://mempool.space/signet/tx/386dbb6aa23fcc35a69d34e3c0f760b185482467abc936196d3def19d54a9c41) |
| APO update v1 -> v2 | [`096e31cc...5601`](https://mempool.space/signet/tx/096e31ccbd8f5460b2730ec4f757ee1b01acf9dde3e3b8cb55fbb534fe195601) |
| APO update v2 -> v3 | [`091309b7...d7f6`](https://mempool.space/signet/tx/091309b73e299436ff12fceda7e54e28c6f1817fdf3405bca3343ad15198d7f6) |
| CTV settlement of v3 | [`13957f49...f9b7`](https://mempool.space/signet/tx/13957f49d01aa21ed2aa28df7aa78f357d51a2a2fbfb434af05fdc75ad0ff9b7) |
| APO rebinding, spend A (signed) | [`03c0577c...f3a4`](https://mempool.space/signet/tx/03c0577c1d47da32804d098187644d0eee18b448aded2f427cd02193c070f3a4) |
| APO rebinding, spend B (same witness, different UTXO) | [`46091190...1a43`](https://mempool.space/signet/tx/46091190c74d8fd4b39be67a2e945a19b021850e7f8d9e378f5eb11722ae1a43) |

Key-free checks: `python examples/verify_onchain.py` (confirmation and TXID of every transaction above) and
[`verify_onchain.py` in eltoo-apo-state-chain](https://github.com/aaron-recompile/eltoo-apo-state-chain)
(claim-by-claim: witnesses, payout splits, the copied APO signature). Write-ups:
[Delving /t/2413](https://delvingbitcoin.org/t/eltoo-state-chain-on-signet-three-rounds-six-transactions-apo-ctv/2413),
[Delving /t/2411](https://delvingbitcoin.org/t/bip-118-signing-from-scratch-on-chain-rebinding-proof/2411).

## Files

| File | Role |
|------|------|
| `rca_taptree_smoke.py` | Single-tree smoke: `--fund`, `--spend ctv\|apo\|csv`, optional `--fund-apo-rebind` / `--spend-apo-rebind` |
| `rca_eltoo_chain.py` | Full `--run` chain: fund → APO → APO → CTV settle |
| `braidpool_config.py` | `bitcoin-cli` RPC to Inquisition |
| `template_common.py` | Fund/broadcast/UTXO helpers |
| `load_local_env.py` | Optional root `.env` loading |

Long-form analysis write-ups stay outside this repo; this folder is **runnable code + this README only**.
