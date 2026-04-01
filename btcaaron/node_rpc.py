"""
btcaaron.node_rpc - lightweight node RPC helpers.

This module intentionally accepts callable RPC adapters instead of managing
credentials or subprocesses. It is designed to integrate with existing
project-specific RPC wrappers (for example, `config.rpc` and `config.rpc_wallet`).
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Callable, Optional, Tuple

RpcFn = Callable[..., Any]
Utxo = Tuple[str, int, int]  # (txid, vout, sats)


def sats_from_rpc_amount(value: Any) -> int:
    """
    Convert RPC amount field to satoshis.

    Supports:
    - `value` in BTC float/str (common in getrawtransaction/scantxoutset)
    - integer satoshis (if already normalized by caller)
    - :class:`decimal.Decimal` (BTC nominal)

    Uses :class:`~decimal.Decimal` instead of ``float * 1e8`` so rounding matches
    Taproot/BIP341 sighash expectations (off-by-one sat breaks Schnorr verification).
    """
    if value is None:
        raise ValueError("Missing amount value")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int((value * Decimal(10**8)).to_integral_value())
    return int((Decimal(str(value)) * Decimal(10**8)).to_integral_value())


def wallet_change_address(rpc_wallet: RpcFn) -> str:
    """
    Get a bech32m change address from wallet RPC.
    """
    return rpc_wallet("getrawchangeaddress", "bech32m") or rpc_wallet(
        "getnewaddress", "change", "bech32m"
    )


def wallet_send_sats(rpc_wallet: RpcFn, address: str, sats: int) -> str:
    """
    Send sats to an address via wallet RPC and return txid.
    """
    return rpc_wallet(
        "sendtoaddress",
        address,
        sats / 1e8,
        "",
        "",
        False,
        False,
        None,
        "unset",
        False,
        1,
    )


def broadcast_tx_hex(rpc: RpcFn, tx_hex: str) -> str:
    """
    Broadcast raw tx hex and return txid.
    """
    return rpc("sendrawtransaction", tx_hex)


def find_utxo_for_address(rpc: RpcFn, address: str, txid_hint: Optional[str] = None) -> Optional[Utxo]:
    """
    Find one UTXO paying to `address`.

    Search order:
    1. If txid_hint provided, inspect that tx first via getrawtransaction
    2. Fallback to scantxoutset addr() scan
    """

    def _from_raw_tx(txid: str) -> Optional[Utxo]:
        try:
            raw = rpc("getrawtransaction", txid, 1)
        except Exception:
            return None
        if not raw:
            return None
        for out in raw.get("vout", []):
            if out.get("scriptPubKey", {}).get("address") == address:
                return txid, int(out["n"]), sats_from_rpc_amount(out.get("value"))
        return None

    if txid_hint:
        hit = _from_raw_tx(txid_hint)
        if hit:
            return hit

    # best-effort cancel previous long scan
    try:
        rpc("scantxoutset", "abort")
    except Exception:
        pass

    scan = rpc("scantxoutset", "start", json.dumps([f"addr({address})"]))
    unspents = scan.get("unspents", [])
    if not unspents:
        return None

    u = unspents[0]
    amt = u.get("value", u.get("amount"))
    if amt is None:
        raise KeyError(f"Unexpected scantxoutset entry without value/amount: {u}")
    return u["txid"], int(u["vout"]), sats_from_rpc_amount(amt)

