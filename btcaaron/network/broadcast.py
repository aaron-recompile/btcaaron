"""
btcaaron.network.broadcast - Parallel broadcast across providers

Whoever returns first wins. No async dependency.
"""

from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .mempool import MempoolProvider
from .blockstream import BlockstreamProvider

from ..errors import BroadcastError


def _try_broadcast(provider, tx_hex: str) -> Optional[str]:
    """Single-provider broadcast. Returns txid or None."""
    return provider.broadcast(tx_hex)


def broadcast_parallel(
    tx_hex: str,
    network: str = "testnet",
) -> str:
    """
    Broadcast to Mempool and Blockstream in parallel.
    First successful response wins.

    Args:
        tx_hex: Raw transaction hex
        network: "testnet" or "mainnet"

    Returns:
        Transaction ID

    Raises:
        BroadcastError: If all providers fail
    """
    providers = [
        MempoolProvider(network=network),
        BlockstreamProvider(network=network),
    ]

    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = {
            executor.submit(_try_broadcast, p, tx_hex): p
            for p in providers
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    return result
            except Exception:
                continue

    raise BroadcastError("All broadcast attempts failed")
