"""
btcaaron - Taproot-focused Bitcoin Toolkit

v0.1.x API (legacy, still supported):
    from btcaaron import WIFKey, quick_transfer, fund_program

v0.2.x API (new):
    from btcaaron import Key, TapTree
"""

__version__ = "0.2.3"

# ══════════════════════════════════════════════════════════════════
# Legacy API (v0.1.x) - backward compatible
# ══════════════════════════════════════════════════════════════════
from .legacy import (
    WIFKey, 
    BTCAddress, 
    BTCTransaction,
    wif_to_addresses, 
    quick_transfer,
    quick_transfer_tprv,
    taproot_balance_from_tprv,
    fund_program,
)

# ══════════════════════════════════════════════════════════════════
# New API (v0.2.x)
# ══════════════════════════════════════════════════════════════════
from .key import Key, derive_wif_from_tprv, taproot_descriptor_from_tprv, wif_secret_bytes
from .bip118 import (
    SIGHASH_ANYPREVOUT,
    SIGHASH_ANYPREVOUTANYSCRIPT,
    SIGHASH_DEFAULT_APO,
    apo_pubkey_bytes,
    bip118_sighash,
)
from .tree import TapTree, TaprootProgram, LeafDescriptor
from .spend import SpendBuilder, Transaction
from .script import (
    Script,
    RawScript,
    ord_inscription_script,
    brc20_mint_json,
    inq_cat_hashlock_script,
    inq_csfs_script,
    inq_ctv_script,
    inq_ctv_template_hash_for_output,
    inq_ctv_template_hash_for_outputs,
    inq_ctv_program_for_output,
    inq_ctv_program_for_outputs,
    inq_apo_checksig_script,
    inq_apo_program,
    inq_internalkey_equal_script,
    inq_internalkey_csfs_script,
    inq_internalkey_equal_program,
    inq_internalkey_csfs_program,
)
from .node_rpc import (
    broadcast_tx_hex,
    find_utxo_for_address,
    sats_from_rpc_amount,
    wallet_change_address,
    wallet_send_sats,
)
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
    "quick_transfer_tprv",
    "taproot_balance_from_tprv",
    "fund_program",
    
    # New API
    "Key",
    "derive_wif_from_tprv",
    "taproot_descriptor_from_tprv",
    "wif_secret_bytes",
    "SIGHASH_ANYPREVOUT",
    "SIGHASH_ANYPREVOUTANYSCRIPT",
    "SIGHASH_DEFAULT_APO",
    "apo_pubkey_bytes",
    "bip118_sighash",
    "TapTree",
    "TaprootProgram",
    "LeafDescriptor",
    "SpendBuilder",
    "Transaction",
    "Script",
    "RawScript",
    "ord_inscription_script",
    "brc20_mint_json",
    "inq_cat_hashlock_script",
    "inq_csfs_script",
    "inq_ctv_script",
    "inq_ctv_template_hash_for_output",
    "inq_ctv_template_hash_for_outputs",
    "inq_ctv_program_for_output",
    "inq_ctv_program_for_outputs",
    "inq_apo_checksig_script",
    "inq_apo_program",
    "inq_internalkey_equal_script",
    "inq_internalkey_csfs_script",
    "inq_internalkey_equal_program",
    "inq_internalkey_csfs_program",
    "broadcast_tx_hex",
    "find_utxo_for_address",
    "sats_from_rpc_amount",
    "wallet_change_address",
    "wallet_send_sats",
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
