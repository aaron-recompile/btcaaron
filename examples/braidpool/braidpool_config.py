"""
RPC helpers for a local Bitcoin Inquisition signet node (``bitcoin-cli -signet``).

Set ``INQUISITION_DATADIR`` and optionally ``INQUISITION_RPC_PORT``, ``BITCOIN_CLI``.
Optional: repository root ``.env`` (loaded via ``load_local_env`` before importing this module).
"""

from __future__ import annotations

import json
import os
import subprocess

try:
    import load_local_env  # noqa: F401
except ImportError:
    pass

RPC_DATADIR = os.environ.get("INQUISITION_DATADIR", "")
CLI_PATH = os.environ.get("BITCOIN_CLI", "bitcoin-cli")
RPC_PORT = os.environ.get("INQUISITION_RPC_PORT", "")


def _check_config() -> None:
    if not RPC_DATADIR:
        raise ValueError(
            "Set INQUISITION_DATADIR (path to your Inquisition node datadir). "
            "Example: export INQUISITION_DATADIR=/path/to/inquisition-data"
        )


def _rpc_cmd_base() -> list:
    cmd = [CLI_PATH, "-signet", f"-datadir={RPC_DATADIR}"]
    if RPC_PORT:
        cmd.append(f"-rpcport={RPC_PORT}")
    return cmd


def rpc(method, *params):
    _check_config()
    cmd = _rpc_cmd_base() + [method]
    for p in params:
        if isinstance(p, (dict, list, bool, type(None))):
            cmd.append(json.dumps(p))
        else:
            cmd.append(str(p))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"RPC error: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()


def rpc_wallet(method, *params, wallet="lab"):
    _check_config()
    cmd = _rpc_cmd_base() + [f"-rpcwallet={wallet}", method]
    for p in params:
        if isinstance(p, (dict, list, bool, type(None))):
            cmd.append(json.dumps(p))
        else:
            cmd.append(str(p))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"RPC error: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()
