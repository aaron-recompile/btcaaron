"""
btcaaron.tree.leaf - Leaf Descriptor

LeafDescriptor holds metadata about each leaf in a Taproot tree.
"""

from dataclasses import dataclass
from typing import Literal, Dict, Any


ScriptType = Literal[
    "HASHLOCK",      # SHA256 hash lock
    "CHECKSIG",      # Single signature
    "MULTISIG",      # N-of-M multisig (CHECKSIGADD)
    "CSV_TIMELOCK",  # Relative timelock (CSV)
    "CLTV_TIMELOCK", # Absolute timelock (CLTV) - future
    "CUSTOM"         # User-defined script
]


@dataclass(frozen=True)
class LeafDescriptor:
    """
    Immutable metadata for a Taproot script leaf.
    
    This is the "contract" between TaprootProgram and SpendBuilder.
    SpendBuilder uses script_type and params to determine how to
    automatically construct the witness.
    
    Attributes:
        label: Unique identifier for this leaf (e.g., "hash", "2of2")
        index: Position in the tree (0-based)
        script_type: Semantic type of the script
        script_hex: Compiled script in hex
        script_asm: Human-readable script
        params: Type-specific parameters for unlock logic
        tapleaf_hash: TapLeaf hash for ControlBlock calculation
    """
    
    label: str
    index: int
    script_type: ScriptType
    script_hex: str
    script_asm: str
    params: Dict[str, Any]
    tapleaf_hash: str
    
    def __repr__(self) -> str:
        return f"LeafDescriptor(label={self.label!r}, type={self.script_type})"
