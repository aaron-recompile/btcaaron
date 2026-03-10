"""
Mainnet readiness smoke checks (no broadcast side effects).

Run from repo root:
  python3 examples/core_test/scenarios/mainnet_readiness_smoke.py
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "btcaaron" not in sys.modules:
    pkg = types.ModuleType("btcaaron")
    pkg.__path__ = [str(ROOT / "btcaaron")]
    sys.modules["btcaaron"] = pkg


def load_btcaaron_symbols():
    try:
        key_cls = importlib.import_module("btcaaron.key").Key
        tap_tree_cls = importlib.import_module("btcaaron.tree.builder").TapTree
        broadcast_error_cls = importlib.import_module("btcaaron.errors").BroadcastError
        return key_cls, tap_tree_cls, broadcast_error_cls
    except Exception as e:
        raise RuntimeError(
            "Cannot import btcaaron Taproot stack. Install btcaaron deps (including bitcoin-utils) first."
        ) from e


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def main() -> None:
    print("=== Mainnet Readiness Smoke ===")
    Key, TapTree, BroadcastError = load_btcaaron_symbols()

    # 1) Network-aware key/tree path should produce bc1p address on mainnet.
    sender = Key.generate(network="mainnet")
    program = TapTree(internal_key=sender, network="mainnet").checksig(sender, label="backup").build()
    require(program.network == "mainnet", "program.network should be mainnet")
    require(program.address.startswith("bc1p"), f"expected bc1p address, got {program.address}")
    print(f"[PASS] mainnet address derivation: {program.address[:16]}...")

    # 2) Build a deterministic tx locally (dummy UTXO, no chain side effects).
    dummy_txid = "11" * 32
    tx = (
        program.keypath()
        .from_utxo(dummy_txid, 0, sats=10_000)
        .to(program.address, 9_500)
        .sign(sender)
        .build()
    )
    require(len(tx.hex) > 20, "tx hex should be non-empty")
    print(f"[PASS] local tx build ok: txid={tx.txid}")

    # 3) Verify routing plan is mainnet.
    plan = tx.broadcast_plan(provider="auto")
    require(plan["network"] == "mainnet", f"expected plan network=mainnet, got {plan['network']}")
    print(f"[PASS] broadcast plan: {plan}")

    # 4) Dry-run should never broadcast.
    dry_run_output = tx.broadcast(provider="auto", dry_run=True)
    require("DRY_RUN network=mainnet" in dry_run_output, "dry run output missing mainnet routing")
    print(f"[PASS] dry-run only: {dry_run_output}")

    # 5) Mainnet safety guard should block actual broadcast by default.
    try:
        tx.broadcast(provider="auto")
        raise RuntimeError("expected mainnet guard to block broadcast")
    except BroadcastError as e:
        require("allow_mainnet=True" in str(e), f"unexpected guard error: {e}")
        print(f"[PASS] mainnet guard active: {e}")

    print("=== ALL 5 CHECKS PASSED ===")


if __name__ == "__main__":
    main()
