"""
Shared fund/spend helpers for the Braidpool covenant demos (local RPC + wallet).
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from btcaaron import (
    broadcast_tx_hex,
    find_utxo_for_address,
    wallet_change_address,
    wallet_send_sats,
)


def print_setup(title: str, address: str, run_hint: str) -> None:
    print(title)
    print(f"Address: {address}")
    print(run_hint)


def read_txid_hint(txid_arg: Optional[str], fund_txid_file: str) -> Optional[str]:
    if txid_arg:
        return txid_arg
    if os.path.exists(fund_txid_file):
        with open(fund_txid_file) as f:
            return f.read().strip()
    return None


def fund_address(address: str, fund_txid_file: str, fund_sats: int = 50_000) -> str:
    from braidpool_config import rpc_wallet

    txid = wallet_send_sats(rpc_wallet, address, fund_sats)
    with open(fund_txid_file, "w") as f:
        f.write(txid)
    return txid


def default_change_address() -> str:
    from braidpool_config import rpc_wallet

    return wallet_change_address(rpc_wallet)


def find_template_utxo_or_exit(address: str, txid_hint: Optional[str]):
    from braidpool_config import rpc

    utxo = find_utxo_for_address(rpc, address, txid_hint=txid_hint)
    if not utxo:
        print("No UTXO. Run --fund first.")
        sys.exit(1)
    return utxo


def broadcast_or_raise(tx_hex: str) -> str:
    from braidpool_config import rpc

    return broadcast_tx_hex(rpc, tx_hex)
