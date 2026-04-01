"""
Multi-round Eltoo-style chain on the same 3-leaf RCA TapTree as ``rca_taptree_smoke``:

  * Round 1 — fund **RCA v1**; CTV commits to **UHPO v1** (50% / 30% / 20%).
  * Round 2 — **APO** spends v1 → **RCA v2**; CTV commits to **UHPO v2** (45% / 35% / 20%).
  * Round 3 — **APO** spends v2 → **RCA v3**; CTV commits to **UHPO v3** (40% / 35% / 25%).
  * Settlement — **CTV** path spends v3 to the three outputs.

Prereqs: same as ``rca_taptree_smoke.py`` (``CAT_DEMO_WIF``, Inquisition RPC, wallet ``lab``).

From the **btcaaron repository root**::

    PYTHONPATH=. python3 examples/braidpool/rca_eltoo_chain.py --run

Verify::

    btcrun inq trace <txid>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_BRAIDPOOL_DIR = os.path.abspath(os.path.dirname(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_BRAIDPOOL_DIR, "..", ".."))
for _p in (_REPO_ROOT, _BRAIDPOOL_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import load_local_env  # noqa: F401

from rca_taptree_smoke import (
    DEFAULT_FEE_SATS,
    SPEND_FEE_SATS,
    build_rca_program,
    broadcast_or_raise,
    key,
)
from template_common import find_template_utxo_or_exit
from btcaaron import wallet_send_sats

_INITIAL_FUND = 50_000


def _rpc_wallet():
    from braidpool_config import rpc_wallet

    return rpc_wallet


def _get_script_pubkey_hex(addr: str) -> str:
    return _rpc_wallet()("getaddressinfo", addr)["scriptPubKey"]


def _split_three(total_out: int, ra: int, rb: int, rc: int) -> tuple[int, int, int]:
    assert ra + rb + rc == 100
    a = total_out * ra // 100
    b = total_out * rb // 100
    c = total_out - a - b
    return a, b, c


def _build_round(pot_sats: int, fee_sats: int, ra: int, rb: int, rc: int):
    rpc = _rpc_wallet()
    total_out = pot_sats - fee_sats
    if total_out <= 0:
        raise ValueError("pot_sats must exceed fee_sats")
    aa, bb, cc = _split_three(total_out, ra, rb, rc)
    addrs = [rpc("getnewaddress", "", "bech32m") for _ in range(3)]
    rows = []
    outputs: list[tuple[int, str]] = []
    for addr, sats in zip(addrs, (aa, bb, cc)):
        spk = _get_script_pubkey_hex(addr)
        rows.append({"address": addr, "sats": sats, "scriptPubKey": spk})
        outputs.append((sats, spk))
    program, th = build_rca_program(outputs)
    return program, th, rows


def _apo_spend_to(program, txid: str, vout: int, sats: int, dest_addr: str, out_sats: int):
    tx = (
        program.spend("apo_update")
        .from_utxo(txid, vout, sats=sats)
        .to(dest_addr, out_sats)
        .sign(key)
        .build()
    )
    return tx


def _ctv_spend(program, state_rows: list, txid: str, vout: int, sats: int):
    b = program.spend("ctv_uhpo").from_utxo(txid, vout, sats=sats).sequence(0xFFFFFFFF)
    for row in state_rows:
        b = b.to(row["address"], int(row["sats"]))
    return b.unlock_with([]).build()


def run_chain() -> None:
    rpcw = _rpc_wallet()
    print("=== Round 1: fund RCA v1 (CTV → UHPO v1: 50/30/20) ===")
    p1, th1, rows1 = _build_round(_INITIAL_FUND, DEFAULT_FEE_SATS, 50, 30, 20)
    tx_fund = wallet_send_sats(rpcw, p1.address, _INITIAL_FUND)
    print(f"  Fund txid: {tx_fund}")
    print(f"  RCA v1 P2TR: {p1.address}")
    print(f"  UHPO v1 template hash: {th1.hex()}")

    u1 = find_template_utxo_or_exit(p1.address, tx_fund)
    out_to_v2 = u1[2] - SPEND_FEE_SATS
    if out_to_v2 <= 0:
        raise ValueError("input too small for APO fee")

    print("\n=== Round 2: APO spend v1 → RCA v2 (CTV → UHPO v2: 45/35/20) ===")
    p2, th2, rows2 = _build_round(out_to_v2, DEFAULT_FEE_SATS, 45, 35, 20)
    tx_apo1 = _apo_spend_to(p1, u1[0], u1[1], u1[2], p2.address, out_to_v2)
    out_apo1 = broadcast_or_raise(tx_apo1.hex)
    print(f"  APO (v1→v2) txid: {out_apo1}")
    print(f"  RCA v2 P2TR: {p2.address}")
    print(f"  UHPO v2 template hash: {th2.hex()}")
    print(
        "  Note: an APO signature for this tx could be precomputed without knowing v1’s "
        "txid (same tapleaf + amount + outputs)."
    )

    u2 = find_template_utxo_or_exit(p2.address, out_apo1)
    out_to_v3 = u2[2] - SPEND_FEE_SATS

    print("\n=== Round 3: APO spend v2 → RCA v3 (CTV → UHPO v3: 40/35/25) ===")
    p3, th3, rows3 = _build_round(out_to_v3, DEFAULT_FEE_SATS, 40, 35, 25)
    tx_apo2 = _apo_spend_to(p2, u2[0], u2[1], u2[2], p3.address, out_to_v3)
    out_apo2 = broadcast_or_raise(tx_apo2.hex)
    print(f"  APO (v2→v3) txid: {out_apo2}")
    print(f"  RCA v3 P2TR: {p3.address}")
    print(f"  UHPO v3 template hash: {th3.hex()}")

    u3 = find_template_utxo_or_exit(p3.address, out_apo2)

    print("\n=== Settlement: CTV spend v3 → UHPO v3 (three outputs) ===")
    tx_ctv = _ctv_spend(p3, rows3, u3[0], u3[1], u3[2])
    out_ctv = broadcast_or_raise(tx_ctv.hex)
    print(f"  CTV (UHPO v3) txid: {out_ctv}")
    for i, row in enumerate(rows3):
        print(f"    vout {i}: {row['sats']} sats → {row['address']}")

    snap = {
        "round1_fund": tx_fund,
        "round2_apo_v1_to_v2": out_apo1,
        "round3_apo_v2_to_v3": out_apo2,
        "settlement_ctv_uhpo_v3": out_ctv,
    }
    path = os.path.join(os.path.dirname(__file__), ".rca_eltoo_chain_last.json")
    with open(path, "w") as f:
        json.dump(snap, f, indent=2)
    print(f"\nWrote txid summary: {path}")


def main() -> None:
    p = argparse.ArgumentParser(description="RCA v1→v2→v3 Eltoo chain + CTV settlement (demo)")
    p.add_argument("--run", action="store_true", help="Run full chain on Inquisition signet")
    args = p.parse_args()
    if not args.run:
        p.print_help()
        sys.exit(0)
    run_chain()


if __name__ == "__main__":
    main()
