"""
btcaaron.network.provider - Provider base class
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class Provider(ABC):
    """
    Abstract base class for network providers.
    """
    
    @abstractmethod
    def broadcast(self, tx_hex: str) -> Optional[str]:
        """
        Broadcast transaction.
        
        Args:
            tx_hex: Raw transaction hex
            
        Returns:
            Transaction ID if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def get_utxos(self, address: str) -> List[Dict]:
        """
        Get UTXOs for an address.
        
        Args:
            address: Bitcoin address
            
        Returns:
            List of UTXO dictionaries
        """
        pass
    
    @abstractmethod
    def get_fee_estimate(self, target_blocks: int = 6) -> float:
        """
        Get fee rate estimate.
        
        Args:
            target_blocks: Target confirmation blocks
            
        Returns:
            Fee rate in sat/vB
        """
        pass
