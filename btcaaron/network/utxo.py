"""
btcaaron.network.utxo - UTXO fetch, balance, and selection

Standalone utilities for querying any address. No WIF/key required.
"""

from typing import List, Dict

from .mempool import MempoolProvider
from .blockstream import BlockstreamProvider


def fetch_utxos(
    address: str,
    network: str = "testnet",
    debug: bool = False
) -> List[Dict]:
    """
    Fetch UTXOs for an address from available APIs.

    Tries Mempool first, then Blockstream.

    Args:
        address: Bitcoin address to query
        network: "testnet" or "mainnet"
        debug: Print progress to stdout

    Returns:
        List of dicts: [{"txid", "vout", "amount"}, ...]
    """
    providers = [
        MempoolProvider(network=network),
        BlockstreamProvider(network=network),
    ]
    for provider in providers:
        try:
            raw = provider.get_utxos(address)
            if raw:
                utxos = [
                    {
                        "txid": u["txid"],
                        "vout": u["vout"],
                        "amount": u.get("value", u.get("amount", 0)),
                    }
                    for u in raw
                ]
                if debug:
                    total = sum(u["amount"] for u in utxos)
                    print(f"  Fetched {len(utxos)} UTXOs, total: {total:,} sats")
                return utxos
        except Exception:
            continue
    if debug:
        print("  All UTXO providers failed")
    return []


def get_balance(address: str, network: str = "testnet", debug: bool = False) -> int:
    """
    Get balance for any address. No key required.

    Args:
        address: Bitcoin address to query
        network: "testnet" or "mainnet"
        debug: Print progress to stdout

    Returns:
        Balance in satoshis
    """
    utxos = fetch_utxos(address, network, debug)
    return sum(u["amount"] for u in utxos)


def select_utxos(
    utxos: List[Dict],
    target_sats: int,
    strategy: str = "largest_first"
) -> List[Dict]:
    """
    Select UTXOs to cover target amount.

    Args:
        utxos: List of {"txid", "vout", "amount"}
        target_sats: Minimum total needed (e.g. amount + fee)
        strategy: "largest_first" (greedy) or "smallest_first"

    Returns:
        Selected UTXOs sufficient for target, or empty if insufficient.
    """
    if not utxos:
        return []
    total = sum(u["amount"] for u in utxos)
    if total < target_sats:
        return []

    reverse = strategy == "largest_first"
    sorted_utxos = sorted(utxos, key=lambda x: x["amount"], reverse=reverse)

    selected = []
    acc = 0
    for u in sorted_utxos:
        selected.append(u)
        acc += u["amount"]
        if acc >= target_sats:
            return selected
    return []
