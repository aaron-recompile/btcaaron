"""
RPC helpers for the eltoo examples — bitcoin-cli to a local Inquisition signet node.

Mirrors the convention used by examples/braidpool/braidpool_config.py so the two
example sets are independent.

Environment variables:
  INQUISITION_DATADIR (required)  — path to the Inquisition node datadir.
  INQUISITION_RPC_PORT (optional) — RPC port if not the datadir default.
  BITCOIN_CLI (optional)          — path to bitcoin-cli (default: "bitcoin-cli").
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any


def _check_config() -> None:
    if not os.environ.get("INQUISITION_DATADIR"):
        raise ValueError(
            "INQUISITION_DATADIR is not set. Point it at your Inquisition node datadir, "
            "e.g. export INQUISITION_DATADIR=/path/to/inquisition-data"
        )


def _bitcoin_cli() -> str:
    return os.environ.get("BITCOIN_CLI", "bitcoin-cli")


def _rpc_cmd_base() -> list[str]:
    _check_config()
    cmd = [_bitcoin_cli(), "-datadir=" + os.environ["INQUISITION_DATADIR"]]
    port = os.environ.get("INQUISITION_RPC_PORT")
    if port:
        cmd.append(f"-rpcport={port}")
    return cmd


def _to_arg(p: Any) -> str:
    if isinstance(p, (dict, list, bool)):
        return json.dumps(p)
    return str(p)


def _run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"bitcoin-cli failed ({' '.join(cmd[:2])} …): {res.stderr.strip()}")
    return res.stdout.strip()


def _maybe_json(out: str) -> Any:
    if not out:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def rpc(method: str, *params: Any) -> Any:
    """Generic RPC call."""
    cmd = _rpc_cmd_base() + [method] + [_to_arg(p) for p in params]
    return _maybe_json(_run(cmd))


def rpc_wallet(method: str, *params: Any, wallet: str = "lab") -> Any:
    """Wallet-scoped RPC call (defaults to wallet 'lab')."""
    cmd = _rpc_cmd_base() + [f"-rpcwallet={wallet}", method] + [_to_arg(p) for p in params]
    return _maybe_json(_run(cmd))
