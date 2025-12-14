"""
btcaaron.explain.program - Program explanation
"""

from dataclasses import dataclass
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..tree.program import TaprootProgram


@dataclass
class ProgramExplanation:
    """Structured explanation of a TaprootProgram."""
    
    program: "TaprootProgram"
    
    def to_text(self) -> str:
        """Generate human-readable text explanation."""
        p = self.program
        lines = [
            "TaprootProgram",
            f"├── Address: {p.address}",
            f"├── Internal Key: {p.internal_key}",
            f"└── Leaves ({p.num_leaves}):",
        ]
        
        for i, label in enumerate(p.leaves):
            leaf = p.leaf(label)
            prefix = "    └──" if i == p.num_leaves - 1 else "    ├──"
            lines.append(f"{prefix} [{i}] \"{label}\": {leaf.script_type}")
        
        return "\n".join(lines)
    
    def to_markdown(self) -> str:
        """Generate Markdown explanation."""
        return f"```\n{self.to_text()}\n```"
    
    def to_dict(self) -> Dict[str, Any]:
        """Generate dictionary representation."""
        p = self.program
        return {
            "address": p.address,
            "internal_key": p.internal_key,
            "merkle_root": p.merkle_root,
            "leaves": [
                {
                    "label": leaf.label,
                    "index": leaf.index,
                    "script_type": leaf.script_type,
                    "script_hex": leaf.script_hex,
                }
                for leaf in [p.leaf(label) for label in p.leaves]
            ]
        }
