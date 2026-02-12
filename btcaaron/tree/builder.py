"""
btcaaron.tree.builder - TapTree Builder

TapTree provides a fluent interface for constructing Taproot script trees.
"""

from typing import List, Optional, Union, TYPE_CHECKING
import hashlib

from ..key import Key
from .leaf import LeafDescriptor
from .program import TaprootProgram

if TYPE_CHECKING:
    from ..script.script import Script, RawScript


class TapTree:
    """
    Taproot Script Tree Builder (Mutable)
    
    Build Taproot trees using a fluent, semantic API.
    Call .build() to freeze the tree into a TaprootProgram.
    
    Example:
        program = (TapTree(internal_key=alice)
            .hashlock("secret", label="hash")
            .multisig(2, [alice, bob], label="2of2")
            .timelock(blocks=144, then=bob, label="csv")
            .checksig(bob, label="backup")
        ).build()
        
        print(program.address)  # tb1p...
    """
    
    def __init__(self, internal_key: Key, network: str = "testnet"):
        """
        Initialize TapTree builder.
        
        Args:
            internal_key: The internal key for key-path spending
            network: "testnet" | "signet" | "mainnet"
        """
        self._internal_key = internal_key
        self._network = network
        self._leaves: List[dict] = []  # Temporary storage before build()
        self._leaf_counter = 0
    
    def _next_index(self) -> int:
        """Get next leaf index"""
        idx = self._leaf_counter
        self._leaf_counter += 1
        return idx
    
    def _ensure_label(self, label: Optional[str]) -> str:
        """Generate label if not provided"""
        if label is None:
            return f"_leaf{self._leaf_counter}"
        return label
    
    # ══════════════════════════════════════════════════════════════
    # Semantic Leaf Methods
    # ══════════════════════════════════════════════════════════════
    
    def hashlock(self, preimage: str, *, label: str = None) -> "TapTree":
        """
        Add a SHA256 hash lock leaf.
        
        Script: OP_SHA256 <hash> OP_EQUALVERIFY OP_TRUE
        Unlock: .unlock(preimage="...")
        
        Args:
            preimage: The secret string (UTF-8)
            label: Unique label for this leaf
        """
        label = self._ensure_label(label)
        preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
        
        self._leaves.append({
            "label": label,
            "index": self._next_index(),
            "script_type": "HASHLOCK",
            "params": {"preimage_hash": preimage_hash},
        })
        return self
    
    def checksig(self, key: Key, *, label: str = None) -> "TapTree":
        """
        Add a single signature leaf.
        
        Script: <x-only-pubkey> OP_CHECKSIG
        Unlock: .sign(key)
        
        Args:
            key: The signing key
            label: Unique label for this leaf
        """
        label = self._ensure_label(label)
        
        self._leaves.append({
            "label": label,
            "index": self._next_index(),
            "script_type": "CHECKSIG",
            "params": {"pubkey": key.xonly},
        })
        return self
    
    def multisig(self, threshold: int, keys: List[Key], *, label: str = None) -> "TapTree":
        """
        Add an N-of-M multisig leaf (Tapscript style with CHECKSIGADD).
        
        Script: OP_0 <pk1> OP_CHECKSIGADD <pk2> OP_CHECKSIGADD ... <n> OP_EQUAL
        Unlock: .sign(key1, key2, ...) - order doesn't matter
        
        Args:
            threshold: Number of required signatures
            keys: List of participating keys
            label: Unique label for this leaf
        """
        label = self._ensure_label(label)
        
        if threshold > len(keys):
            raise ValueError(f"Threshold {threshold} exceeds number of keys {len(keys)}")
        
        self._leaves.append({
            "label": label,
            "index": self._next_index(),
            "script_type": "MULTISIG",
            "params": {
                "threshold": threshold,
                "pubkeys": [k.xonly for k in keys],
            },
        })
        return self
    
    def timelock(self, *, blocks: int = None, timestamp: int = None,
                 then: Key, label: str = None) -> "TapTree":
        """
        Add a CSV (relative) timelock leaf.
        
        Script: <sequence> OP_CHECKSEQUENCEVERIFY OP_DROP <pubkey> OP_CHECKSIG
        Unlock: .sign(key) - nSequence is set automatically
        
        Args:
            blocks: Relative block count (mutually exclusive with timestamp)
            timestamp: Relative seconds (mutually exclusive with blocks)
            then: Key that can spend after timelock expires
            label: Unique label for this leaf
        """
        label = self._ensure_label(label)
        
        if blocks is None and timestamp is None:
            raise ValueError("Must specify either blocks or timestamp")
        if blocks is not None and timestamp is not None:
            raise ValueError("Cannot specify both blocks and timestamp")
        
        # Calculate sequence value
        if blocks is not None:
            sequence_value = blocks  # Simple case: just block count
        else:
            # Timestamp: set bit 22 (0x400000) + seconds/512
            sequence_value = 0x400000 | (timestamp // 512)
        
        self._leaves.append({
            "label": label,
            "index": self._next_index(),
            "script_type": "CSV_TIMELOCK",
            "params": {
                "sequence_value": sequence_value,
                "blocks": blocks,
                "timestamp": timestamp,
                "pubkey": then.xonly,
            },
        })
        return self
    
    def custom(self, script: Union["Script", "RawScript"], *, label: str,
               unlock_hint: str = None) -> "TapTree":
        """
        Add a custom script leaf.
        
        Unlock: .unlock_with([witness_element_1, ...])
        
        Args:
            script: Script or RawScript (RawScript for non-standard opcodes e.g. Inquisition)
            label: Required - custom scripts must have a label
            unlock_hint: Description of how to unlock (for explain())
        """
        self._leaves.append({
            "label": label,
            "index": self._next_index(),
            "script_type": "CUSTOM",
            "params": {
                "script": script,
                "unlock_hint": unlock_hint,
            },
        })
        return self
    
    # ══════════════════════════════════════════════════════════════
    # Build
    # ══════════════════════════════════════════════════════════════
    
    def build(self) -> TaprootProgram:
        """
        Freeze the tree and create a TaprootProgram.
        
        After calling build(), the TapTree should not be modified
        (though this is not enforced).
        
        Returns:
            TaprootProgram: Immutable program with address and spend methods
        """
        return TaprootProgram(
            internal_key=self._internal_key,
            leaves=self._leaves,
            network=self._network,
        )
    
    def __repr__(self) -> str:
        labels = [leaf["label"] for leaf in self._leaves]
        return f"TapTree(leaves={labels})"
