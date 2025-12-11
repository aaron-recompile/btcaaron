"""
btcaaron.spend.transaction - Transaction

Represents a built transaction ready for broadcast.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bitcoinutils.transactions import Transaction as BUTransaction
    from ..tree.program import TaprootProgram
    from ..tree.leaf import LeafDescriptor


class Transaction:
    """
    Built Transaction (Immutable)
    
    Represents a signed transaction ready for broadcast.
    """
    
    def __init__(self, bu_tx: "BUTransaction", program: "TaprootProgram",
                 leaf: Optional["LeafDescriptor"], input_sats: int):
        """Internal constructor. Use SpendBuilder.build()."""
        self._tx = bu_tx
        self._program = program
        self._leaf = leaf
        self._input_sats = input_sats
    
    @property
    def txid(self) -> str:
        """Transaction ID (little-endian hex)"""
        return self._tx.get_txid()
    
    @property
    def hex(self) -> str:
        """Raw transaction hex"""
        return self._tx.serialize()
    
    @property
    def size(self) -> int:
        """Transaction size in bytes"""
        return len(self.hex) // 2
    
    @property
    def vsize(self) -> int:
        """Virtual size in vbytes"""
        # Simplified: actual vsize calculation is more complex
        return self._tx.get_vsize() if hasattr(self._tx, 'get_vsize') else self.size
    
    @property
    def fee(self) -> int:
        """Transaction fee in satoshis"""
        output_total = sum(out.amount for out in self._tx.outputs)
        return self._input_sats - output_total
    
    @property
    def fee_rate(self) -> float:
        """Fee rate in sat/vB"""
        return self.fee / self.vsize if self.vsize > 0 else 0
    
    def broadcast(self, *, provider: str = "auto", explain: bool = False) -> str:
        """
        Broadcast transaction to the network.
        
        Args:
            provider: "mempool" | "blockstream" | "auto"
            explain: Print explanation before broadcasting
            
        Returns:
            Transaction ID if successful
        """
        if explain:
            print(self.explain().to_text())
        
        from ..network.mempool import MempoolProvider
        from ..network.blockstream import BlockstreamProvider
        from ..errors import BroadcastError
        
        providers = []
        if provider == "auto":
            providers = [MempoolProvider(), BlockstreamProvider()]
        elif provider == "mempool":
            providers = [MempoolProvider()]
        elif provider == "blockstream":
            providers = [BlockstreamProvider()]
        
        for p in providers:
            try:
                result = p.broadcast(self.hex)
                if result:
                    return result
            except Exception:
                continue
        
        raise BroadcastError("All broadcast attempts failed")
    
    def explain(self) -> "TransactionExplanation":
        """
        Get structured explanation of this transaction.
        """
        from ..explain.transaction import TransactionExplanation
        return TransactionExplanation(self)
    
    def __repr__(self) -> str:
        return f"Transaction(txid={self.txid[:16]}..., fee={self.fee} sats)"
