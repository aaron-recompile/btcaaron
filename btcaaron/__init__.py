"""
btcaaron - Taproot-focused Bitcoin Toolkit

v0.1.x API (legacy, still supported):
    from btcaaron import WIFKey, quick_transfer, fund_program

v0.2.x API (new):
    from btcaaron import Key, TapTree
"""

__version__ = "0.2.1"

# ══════════════════════════════════════════════════════════════════
# Legacy API (v0.1.x) - backward compatible
# ══════════════════════════════════════════════════════════════════
from .legacy import (
    WIFKey, 
    BTCAddress, 
    BTCTransaction,
    wif_to_addresses, 
    quick_transfer,
    fund_program,
)

# ══════════════════════════════════════════════════════════════════
# New API (v0.2.x)
# ══════════════════════════════════════════════════════════════════
from .key import Key
from .tree import TapTree, TaprootProgram, LeafDescriptor
from .spend import SpendBuilder, Transaction
from .script import Script, RawScript
from .psbt import Psbt, PsbtInput, PsbtV2, PsbtV2Input
from .errors import (
    BtcAaronError,
    BuildError,
    BroadcastError,
    ValidationError,
)

__all__ = [
    # Version
    "__version__",
    
    # Legacy API
    "WIFKey", 
    "BTCAddress", 
    "BTCTransaction",
    "wif_to_addresses", 
    "quick_transfer",
    "fund_program",
    
    # New API
    "Key",
    "TapTree",
    "TaprootProgram",
    "LeafDescriptor",
    "SpendBuilder",
    "Transaction",
    "Script",
    "RawScript",
    "Psbt",
    "PsbtInput",
    "PsbtV2",
    "PsbtV2Input",
    
    # Errors
    "BtcAaronError",
    "BuildError",
    "BroadcastError",
    "ValidationError",
]
