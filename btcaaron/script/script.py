"""
btcaaron.script.script - Script class

Wrapper for Bitcoin scripts with helper methods.
"""

from typing import List


class Script:
    """
    Bitcoin Script wrapper.
    
    Provides convenient construction methods for custom scripts.
    
    Example:
        script = Script.from_ops(["OP_DUP", "OP_HASH160", hash_hex, "OP_EQUALVERIFY", "OP_CHECKSIG"])
        script = Script.from_asm("OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG")
        script = Script.from_hex("76a914...")
    """
    
    def __init__(self, bu_script):
        """Internal constructor."""
        self._internal = bu_script
    
    @classmethod
    def from_ops(cls, ops: List[str]) -> "Script":
        """
        Create script from list of operations.
        
        Args:
            ops: List of opcodes and data pushes
        """
        from bitcoinutils.script import Script as BUScript
        return cls(BUScript(ops))
    
    @classmethod
    def from_asm(cls, asm: str) -> "Script":
        """
        Create script from ASM string.
        
        Args:
            asm: Space-separated opcodes and data
        """
        ops = asm.split()
        return cls.from_ops(ops)
    
    @classmethod
    def from_hex(cls, hex_str: str) -> "Script":
        """
        Create script from hex string.
        
        Args:
            hex_str: Raw script hex
        """
        from bitcoinutils.script import Script as BUScript
        return cls(BUScript.from_raw(hex_str))
    
    def to_hex(self) -> str:
        """Get script as hex string."""
        return self._internal.to_hex()
    
    def to_asm(self) -> str:
        """Get script as ASM string."""
        return str(self._internal)
    
    def __repr__(self) -> str:
        return f"Script({self.to_asm()[:50]}...)"
