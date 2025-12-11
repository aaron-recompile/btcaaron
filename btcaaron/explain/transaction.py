"""
btcaaron.explain.transaction - Transaction explanation
"""

from dataclasses import dataclass
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..spend.transaction import Transaction


@dataclass
class TransactionExplanation:
    """Structured explanation of a Transaction."""
    
    tx: "Transaction"
    
    def to_text(self) -> str:
        """Generate human-readable text explanation."""
        t = self.tx
        lines = [
            "Transaction Details",
            f"├── TXID: {t.txid}",
            f"├── Size: {t.size} bytes",
            f"├── Fee: {t.fee} sats ({t.fee_rate:.2f} sat/vB)",
        ]
        
        if t._leaf:
            lines.append(f"├── Spend Path: Script Path, Leaf \"{t._leaf.label}\"")
        else:
            lines.append(f"├── Spend Path: Key Path")
        
        lines.append(f"└── Outputs: {len(t._tx.outputs)}")
        
        return "\n".join(lines)
    
    def to_markdown(self) -> str:
        """Generate Markdown explanation."""
        return f"```\n{self.to_text()}\n```"
    
    def to_dict(self) -> Dict[str, Any]:
        """Generate dictionary representation."""
        t = self.tx
        return {
            "txid": t.txid,
            "hex": t.hex,
            "size": t.size,
            "vsize": t.vsize,
            "fee": t.fee,
            "fee_rate": t.fee_rate,
            "spend_type": "SCRIPT_PATH" if t._leaf else "KEY_PATH",
            "leaf_label": t._leaf.label if t._leaf else None,
        }
