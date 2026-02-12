"""
btcaaron.spend.builder - SpendBuilder

SpendBuilder provides a fluent interface for constructing spending transactions.
"""

from typing import List, Optional, TYPE_CHECKING

from ..key import Key
from .transaction import Transaction

if TYPE_CHECKING:
    from ..tree.program import TaprootProgram
    from ..tree.leaf import LeafDescriptor


class SpendBuilder:
    """
    Transaction Spend Builder (Mutable)
    
    Fluent interface for building spending transactions.
    
    Example:
        tx = (program.spend("hash")
            .from_utxo("abc123...", 0, sats=1200)
            .to("tb1p...", 666)
            .unlock(preimage="secret")
            .build())
    """
    
    def __init__(self, program: "TaprootProgram", leaf: Optional["LeafDescriptor"], 
                 is_keypath: bool):
        """
        Internal constructor. Use program.spend() or program.keypath().
        """
        self._program = program
        self._leaf = leaf
        self._is_keypath = is_keypath
        
        # Transaction data
        self._utxo_txid: Optional[str] = None
        self._utxo_vout: Optional[int] = None
        self._utxo_sats: Optional[int] = None
        
        self._outputs: List[tuple] = []  # [(address, sats), ...]
        
        # Unlock data
        self._preimage: Optional[str] = None
        self._signatures: List[Key] = []
        self._custom_witness: Optional[List[str]] = None
        
        # Transaction options
        self._sequence: Optional[int] = None  # Custom nSequence value
    
    # ══════════════════════════════════════════════════════════════
    # Input
    # ══════════════════════════════════════════════════════════════
    
    def from_utxo(self, txid: str, vout: int = None, *, sats: int) -> "SpendBuilder":
        """
        Specify the input UTXO.
        
        Args:
            txid: Transaction ID (can be "txid:vout" format)
            vout: Output index (if not in txid string)
            sats: Amount in satoshis
        """
        if ":" in txid and vout is None:
            txid, vout_str = txid.split(":")
            vout = int(vout_str)
        
        self._utxo_txid = txid
        self._utxo_vout = vout
        self._utxo_sats = sats
        return self
    
    # ══════════════════════════════════════════════════════════════
    # Output
    # ══════════════════════════════════════════════════════════════
    
    def to(self, address: str, sats: int) -> "SpendBuilder":
        """
        Add an output.
        
        Args:
            address: Destination address
            sats: Amount in satoshis
        """
        self._outputs.append((address, sats))
        return self
    
    # ══════════════════════════════════════════════════════════════
    # Transaction Options
    # ══════════════════════════════════════════════════════════════
    
    def sequence(self, value: int) -> "SpendBuilder":
        """
        Set custom nSequence value for the input.
        
        Common values:
            0xffffffff  — Final, RBF disabled
            0xfffffffd  — RBF enabled (default for non-timelock)
            
        For CSV_TIMELOCK scripts, nSequence is set automatically
        from the timelock parameters. This method overrides that.
        
        Args:
            value: nSequence as integer (e.g. 0xffffffff)
        """
        self._sequence = value
        return self
    
    # ══════════════════════════════════════════════════════════════
    # Unlock / Sign
    # ══════════════════════════════════════════════════════════════
    
    def unlock(self, *, preimage: str = None, **kwargs) -> "SpendBuilder":
        """
        Provide unlock data (for non-signature scripts like HASHLOCK).
        
        Args:
            preimage: For HASHLOCK scripts
        """
        if preimage is not None:
            self._preimage = preimage
        return self
    
    def sign(self, *keys: Key) -> "SpendBuilder":
        """
        Provide signing keys.
        
        For MULTISIG: order doesn't matter, will be sorted internally.
        For CSV_TIMELOCK: nSequence is set automatically.
        For KEYPATH: key should be the internal key.
        """
        self._signatures.extend(keys)
        return self
    
    def unlock_with(self, witness_elements: List[str]) -> "SpendBuilder":
        """
        Manually provide witness stack (for CUSTOM scripts).
        
        Args:
            witness_elements: List of hex strings for witness stack
        """
        self._custom_witness = witness_elements
        return self
    
    # ══════════════════════════════════════════════════════════════
    # Build
    # ══════════════════════════════════════════════════════════════
    
    def build(self) -> Transaction:
        """
        Build the final transaction.
        
        Returns:
            Transaction object ready for broadcast
        """
        from ..errors import BuildError
        
        # Validate inputs
        if self._utxo_txid is None:
            raise BuildError("No UTXO specified. Call .from_utxo() first.")
        if not self._outputs:
            raise BuildError("No outputs specified. Call .to() first.")
        
        # Build transaction based on spend type
        if self._is_keypath:
            return self._build_keypath()
        else:
            return self._build_script_path()
    
    def _build_keypath(self) -> Transaction:
        """Build key-path spending transaction."""
        from bitcoinutils.transactions import Transaction as BUTransaction
        from bitcoinutils.transactions import TxInput, TxOutput, TxWitnessInput
        from bitcoinutils.utils import to_satoshis
        import struct
        
        # Create input
        txin = TxInput(self._utxo_txid, self._utxo_vout)
        
        # Apply custom sequence if set
        if self._sequence is not None:
            txin.sequence = struct.pack('<I', self._sequence)
        
        # Create outputs
        txouts = []
        for addr_str, sats in self._outputs:
            addr_obj = self._address_from_string(addr_str)
            txouts.append(TxOutput(sats, addr_obj.to_script_pub_key()))
        
        # Create transaction
        tx = BUTransaction([txin], txouts, has_segwit=True)
        
        # Sign with internal key (tweaked)
        if not self._signatures:
            from ..errors import BuildError
            raise BuildError("Key-path spending requires .sign(internal_key)")
        
        key = self._signatures[0]
        scripts_for_tweak = (
            self._program._merkle_root
            if getattr(self._program, '_use_tapmath', False)
            else self._program._tree
        )
        sig = key._internal.sign_taproot_input(
            tx, 0,
            [self._program._addr_obj.to_script_pub_key()],
            [self._utxo_sats],
            script_path=False,
            tapleaf_scripts=scripts_for_tweak
        )
        
        tx.witnesses.append(TxWitnessInput([sig]))
        
        return Transaction(tx, self._program, None, self._utxo_sats)
    
    def _build_script_path(self) -> Transaction:
        """Build script-path spending transaction."""
        from bitcoinutils.transactions import Transaction as BUTransaction
        from bitcoinutils.transactions import TxInput, TxOutput, TxWitnessInput, Sequence
        from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
        import struct
        
        leaf = self._leaf
        script_type = leaf.script_type
        
        # Create input with appropriate sequence
        if self._sequence is not None:
            # User-specified sequence takes priority
            txin = TxInput(self._utxo_txid, self._utxo_vout)
            txin.sequence = struct.pack('<I', self._sequence)
        elif script_type == "CSV_TIMELOCK":
            seq = Sequence(TYPE_RELATIVE_TIMELOCK, leaf.params["sequence_value"])
            txin = TxInput(self._utxo_txid, self._utxo_vout, sequence=seq.for_input_sequence())
        else:
            txin = TxInput(self._utxo_txid, self._utxo_vout)
            txin.sequence = struct.pack('<I', 0xfffffffd)  # RBF enabled
        
        # Create outputs
        txouts = []
        for addr_str, sats in self._outputs:
            addr_obj = self._address_from_string(addr_str)
            txouts.append(TxOutput(sats, addr_obj.to_script_pub_key()))
        
        # Create transaction
        tx = BUTransaction([txin], txouts, has_segwit=True)
        
        # Get script and control block (program.control_block handles both bitcoinutils and tapmath paths)
        script = self._program._scripts[leaf.index]
        cb_hex = self._program.control_block(leaf.index)
        
        # Build witness based on script type
        witness_elements = []
        
        if script_type == "HASHLOCK":
            if self._preimage is None:
                from ..errors import BuildError
                raise BuildError("HASHLOCK requires .unlock(preimage='...')")
            witness_elements.append(self._preimage.encode('utf-8').hex())
            
        elif script_type == "CHECKSIG":
            if not self._signatures:
                from ..errors import BuildError
                raise BuildError("CHECKSIG requires .sign(key)")
            
            key = self._signatures[0]
            sig = key._internal.sign_taproot_input(
                tx, 0,
                [self._program._addr_obj.to_script_pub_key()],
                [self._utxo_sats],
                script_path=True,
                tapleaf_script=script,
                tweak=False
            )
            witness_elements.append(sig)
            
        elif script_type == "MULTISIG":
            if len(self._signatures) < leaf.params["threshold"]:
                from ..errors import BuildError
                raise BuildError(f"MULTISIG requires at least {leaf.params['threshold']} signatures")
            
            # Sign with each key and order correctly
            # In CHECKSIGADD, signatures are consumed in order: first key, second key, etc.
            # But witness stack is LIFO, so we need reverse order
            pubkeys = leaf.params["pubkeys"]
            sigs_by_pubkey = {}
            
            for key in self._signatures:
                sig = key._internal.sign_taproot_input(
                    tx, 0,
                    [self._program._addr_obj.to_script_pub_key()],
                    [self._utxo_sats],
                    script_path=True,
                    tapleaf_script=script,
                    tweak=False
                )
                sigs_by_pubkey[key.xonly] = sig
            
            # Order signatures: last pubkey's sig first in witness
            for pk in reversed(pubkeys):
                if pk in sigs_by_pubkey:
                    witness_elements.append(sigs_by_pubkey[pk])
                    
        elif script_type == "CSV_TIMELOCK":
            if not self._signatures:
                from ..errors import BuildError
                raise BuildError("CSV_TIMELOCK requires .sign(key)")
            
            key = self._signatures[0]
            sig = key._internal.sign_taproot_input(
                tx, 0,
                [self._program._addr_obj.to_script_pub_key()],
                [self._utxo_sats],
                script_path=True,
                tapleaf_script=script,
                tweak=False
            )
            witness_elements.append(sig)
            
        elif script_type == "CUSTOM":
            if self._custom_witness is None:
                from ..errors import BuildError
                raise BuildError("CUSTOM script requires .unlock_with([...])")
            witness_elements.extend(self._custom_witness)
        
        # Add script and control block (script has to_hex for both Script and RawScript)
        witness_elements.append(script.to_hex())
        witness_elements.append(cb_hex)
        
        tx.witnesses.append(TxWitnessInput(witness_elements))
        
        return Transaction(tx, self._program, leaf, self._utxo_sats)
    
    def _address_from_string(self, address: str):
        """Create address object from string."""
        from bitcoinutils.keys import P2pkhAddress, P2wpkhAddress, P2trAddress
        
        if address.startswith(('1', 'm', 'n')):
            return P2pkhAddress(address)
        elif address.startswith(('bc1q', 'tb1q')):
            return P2wpkhAddress(address)
        elif address.startswith(('bc1p', 'tb1p')):
            return P2trAddress(address)
        else:
            raise ValueError(f"Unsupported address format: {address}")
