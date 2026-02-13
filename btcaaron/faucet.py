"""
btcaaron.faucet - Testnet faucet client

Zero config: pip install btcaaron, then faucet.drip("tb1q...")

Requires a running faucet server. Default URL is configurable via FAUCET_URL env.
"""

import os
import requests

DEFAULT_FAUCET_URL = os.environ.get("FAUCET_URL", "https://faucet.bitcoincoding.dev")
TIMEOUT = 30


def drip(address: str, *, url: str = None) -> str:
    """
    Claim testnet coins. Returns txid.

    Args:
        address: Bitcoin testnet address (tb1q..., tb1p..., m..., n...)
        url: Override faucet server URL (default: FAUCET_URL env or bitcoincoding.dev)

    Returns:
        Transaction ID

    Raises:
        requests.HTTPError: On 4xx/5xx
        ValueError: On invalid response
    """
    base = url or DEFAULT_FAUCET_URL
    r = requests.post(
        f"{base.rstrip('/')}/drip",
        json={"address": address},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    txid = data.get("txid")
    if not txid or len(txid) != 64:
        raise ValueError(f"Invalid drip response: {data}")
    return txid


def status(*, url: str = None) -> dict:
    """
    Check faucet balance and health.

    Returns:
        {"balance_sats", "drip_amount", "remaining_drips", "network"}
    """
    base = url or DEFAULT_FAUCET_URL
    r = requests.get(f"{base.rstrip('/')}/status", timeout=10)
    r.raise_for_status()
    return r.json()
