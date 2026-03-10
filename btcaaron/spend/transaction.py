"""
btcaaron.spend.transaction - Transaction

Represents a built transaction ready for broadcast.
"""

from typing import Optional, TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from bitcoinutils.transactions import Transaction as BUTransaction
    from ..tree.program import TaprootProgram
    from ..tree.leaf import LeafDescriptor
    from ..explain.transaction import TransactionExplanation


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

    def _broadcast_network(self) -> str:
        """
        Network used for public API broadcast providers.

        regtest has no public explorer endpoint and signet-family networks are
        treated as testnet-like for address/endpoint compatibility.
        """
        n = getattr(self._program, "_network", "testnet")
        if n == "mainnet":
            return "mainnet"
        if n == "regtest":
            return "regtest"
        return "testnet"

    def broadcast_plan(self, provider: str = "auto") -> Dict[str, object]:
        """
        Return a side-effect-free plan for broadcast routing.
        """
        if provider not in {"auto", "mempool", "blockstream"}:
            raise ValueError(f"Unsupported provider: {provider}")
        network = self._broadcast_network()
        provider_order: List[str]
        if provider == "auto":
            provider_order = ["mempool", "blockstream"]
        else:
            provider_order = [provider]
        return {
            "network": network,
            "provider": provider,
            "provider_order": provider_order,
            "txid": self.txid,
            "vsize": self.vsize,
            "fee": self.fee,
        }
    
    def broadcast(
        self,
        *,
        provider: str = "auto",
        explain: bool = False,
        allow_mainnet: bool = False,
        dry_run: bool = False,
    ) -> str:
        """
        Broadcast transaction to the network.
        
        Args:
            provider: "mempool" | "blockstream" | "auto"
            explain: Print explanation before broadcasting
            allow_mainnet: Must be True to broadcast on mainnet
            dry_run: If True, do not broadcast; return planning string
            
        Returns:
            Transaction ID if successful, or dry-run plan string
        """
        if explain:
            print(self.explain().to_text())
        
        from ..network.mempool import MempoolProvider
        from ..network.blockstream import BlockstreamProvider
        from ..errors import BroadcastError

        if provider not in {"auto", "mempool", "blockstream"}:
            raise BroadcastError(f"Unsupported provider: {provider}")

        plan = self.broadcast_plan(provider=provider)
        network = plan["network"]

        if dry_run:
            return (
                f"DRY_RUN network={network} provider={provider} "
                f"order={','.join(plan['provider_order'])} txid={self.txid}"
            )

        if network == "regtest":
            raise BroadcastError(
                "Regtest transactions should be broadcast via local node RPC, "
                "not public explorer APIs."
            )
        if network == "mainnet" and not allow_mainnet:
            raise BroadcastError(
                "Mainnet broadcast is disabled by default. "
                "Re-run with allow_mainnet=True after manual review."
            )
        
        providers = []
        if provider == "auto":
            providers = [MempoolProvider(network=network), BlockstreamProvider(network=network)]
        elif provider == "mempool":
            providers = [MempoolProvider(network=network)]
        elif provider == "blockstream":
            providers = [BlockstreamProvider(network=network)]
        
        errors = []
        for p in providers:
            try:
                result = p.broadcast(self.hex)
                if result:
                    return result
            except Exception as e:
                errors.append(f"{p.__class__.__name__}: {e}")
        err_msg = "All broadcast attempts failed"
        if errors:
            err_msg += f" ({'; '.join(errors)})"
        raise BroadcastError(err_msg)
    
    def explain(self) -> "TransactionExplanation":
        """
        Get structured explanation of this transaction.
        """
        from ..explain.transaction import TransactionExplanation
        return TransactionExplanation(self)
    
    def __repr__(self) -> str:
        return f"Transaction(txid={self.txid[:16]}..., fee={self.fee} sats)"
