"""
btcaaron.network.blockstream - Blockstream.info provider
"""

from typing import List, Dict, Optional
import requests

from .provider import Provider

TIMEOUT = 5


class BlockstreamProvider(Provider):
    """Blockstream.info API provider."""
    
    def __init__(self, network: str = "testnet"):
        if network == "testnet":
            self.base_url = "https://blockstream.info/testnet/api"
        else:
            self.base_url = "https://blockstream.info/api"
    
    def broadcast(self, tx_hex: str) -> Optional[str]:
        try:
            response = requests.post(
                f"{self.base_url}/tx",
                data=tx_hex,
                timeout=TIMEOUT,
                headers={'Content-Type': 'text/plain'}
            )
            if response.status_code == 200:
                txid = response.text.strip()
                if len(txid) == 64:
                    return txid
            # Surface API error for debugging
            raise ValueError(f"HTTP {response.status_code}: {response.text[:200]}")
        except requests.RequestException as e:
            raise ValueError(str(e))
    
    def get_utxos(self, address: str) -> List[Dict]:
        try:
            response = requests.get(
                f"{self.base_url}/address/{address}/utxo",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []
    
    def get_fee_estimate(self, target_blocks: int = 6) -> float:
        try:
            response = requests.get(
                f"{self.base_url}/fee-estimates",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data.get(str(target_blocks), 5.0)
        except Exception:
            pass
        return 5.0
