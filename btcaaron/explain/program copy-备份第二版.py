"""
btcaaron.tree.program - TaprootProgram

TaprootProgram represents a frozen Taproot script tree.
"""

from typing import List, Dict, Any, Union, Optional, TYPE_CHECKING

from ..key import Key
from .leaf import LeafDescriptor

if TYPE_CHECKING:
    from ..spend.builder import SpendBuilder


class TaprootProgram:
    """
    Frozen Taproot Script Tree (Immutable)
    
    Created by TapTree.build(). Provides address, Merkle info,
    and spending entry points.
    
    Example:
        print(program.address)      # tb1p...
        print(program.leaves)       # ["hash", "2of2", "csv", "bob"]
        
        tx = program.spend("hash").from_utxo(...).to(...).build()
    """
    
    def __init__(self, internal_key: Key, leaves: List[dict], network: str):
        """
        Internal constructor. Use TapTree.build() instead.
        """
        self._internal_key = internal_key
        self._network = network
        self._raw_leaves = leaves
        
        # Build leaf descriptors and compute Taproot data
        self._leaf_descriptors: Dict[str, LeafDescriptor] = {}
        self._leaf_by_index: Dict[int, LeafDescriptor] = {}
        self._scripts = []  # For bitcoinutils
        self._address: Optional[str] = None
        self._merkle_root: Optional[str] = None
        
        self._compile()
    
    def _compile(self):
        """Compile leaves into scripts and compute Taproot address."""
        from bitcoinutils.script import Script
        from bitcoinutils.transactions import Sequence
        from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
        
        scripts = []
        
        for leaf_data in self._raw_leaves:
            script_type = leaf_data["script_type"]
            params = leaf_data["params"]
            label = leaf_data["label"]
            index = leaf_data["index"]
            
            # Generate script based on type
            if script_type == "HASHLOCK":
                # Matches debug: ['OP_SHA256', hash_hex, 'OP_EQUALVERIFY', 'OP_TRUE']
                script = Script([
                    'OP_SHA256',
                    params["preimage_hash"],
                    'OP_EQUALVERIFY',
                    'OP_TRUE'
                ])
                
            elif script_type == "CHECKSIG":
                # Matches debug: [pubkey_hex, 'OP_CHECKSIG']
                script = Script([
                    params["pubkey"],
                    'OP_CHECKSIG'
                ])
                
            elif script_type == "MULTISIG":
                # Matches debug: ['OP_0', pk1, 'OP_CHECKSIGADD', pk2, 'OP_CHECKSIGADD', 'OP_2', 'OP_EQUAL']
                ops = ["OP_0"]
                for pk in params["pubkeys"]:
                    ops.append(pk)
                    ops.append("OP_CHECKSIGADD")
                # threshold 2 -> "OP_2"
                ops.append(f"OP_{params['threshold']}")
                ops.append("OP_EQUAL")
                script = Script(ops)
                
            elif script_type == "CSV_TIMELOCK":
                # Matches debug: seq.for_script() returns int, which Script accepts
                # params stores the actual block count, not sequence_value
                blocks = params.get("blocks") or params.get("sequence_value")
                seq = Sequence(TYPE_RELATIVE_TIMELOCK, blocks)
                script = Script([
                    seq.for_script(),  # Returns int like 2
                    "OP_CHECKSEQUENCEVERIFY",
                    "OP_DROP",
                    params["pubkey"],
                    "OP_CHECKSIG"
                ])
                
            elif script_type == "CUSTOM":
                script = params["script"]._internal  # Get underlying Script
                
            else:
                raise ValueError(f"Unknown script type: {script_type}")
            
            scripts.append(script)
            
            # Create LeafDescriptor
            descriptor = LeafDescriptor(
                label=label,
                index=index,
                script_type=script_type,
                script_hex=script.to_hex(),
                script_asm=str(script),
                params=params,
                tapleaf_hash="",  # TODO: Compute actual tapleaf hash
            )
            
            self._leaf_descriptors[label] = descriptor
            self._leaf_by_index[index] = descriptor
        
        self._scripts = scripts
        
        # Build tree structure for bitcoinutils
        # For 4 leaves: [[script0, script1], [script2, script3]]
        if len(scripts) == 0:
            tree = None
        elif len(scripts) == 1:
            tree = scripts[0]
        elif len(scripts) == 2:
            tree = [scripts[0], scripts[1]]
        elif len(scripts) == 4:
            tree = [[scripts[0], scripts[1]], [scripts[2], scripts[3]]]
        else:
            # Generic tree building for other sizes
            # TODO: Implement balanced tree construction
            tree = scripts
        
        self._tree = tree
        
        # Compute address
        if tree is None:
            addr = self._internal_key._internal_pub.get_taproot_address()
        else:
            addr = self._internal_key._internal_pub.get_taproot_address(tree)
        
        self._address = addr.to_string()
        self._addr_obj = addr
    
    # ══════════════════════════════════════════════════════════════
    # Properties
    # ══════════════════════════════════════════════════════════════
    
    @property
    def address(self) -> str:
        """Taproot address (tb1p... or bc1p...)"""
        return self._address
    
    @property
    def internal_key(self) -> str:
        """Internal public key (x-only hex)"""
        return self._internal_key.xonly
    
    @property
    def merkle_root(self) -> Optional[str]:
        """Merkle root (32 bytes hex), None if no scripts"""
        return self._merkle_root
    
    @property
    def leaves(self) -> List[str]:
        """List of leaf labels in index order"""
        sorted_leaves = sorted(self._leaf_descriptors.values(), key=lambda x: x.index)
        return [leaf.label for leaf in sorted_leaves]
    
    @property
    def num_leaves(self) -> int:
        """Number of leaves"""
        return len(self._leaf_descriptors)
    
    # ══════════════════════════════════════════════════════════════
    # Leaf Access
    # ══════════════════════════════════════════════════════════════
    
    def leaf(self, label_or_index: Union[str, int]) -> LeafDescriptor:
        """
        Get leaf descriptor by label or index.
        
        Args:
            label_or_index: Leaf label (recommended) or index
            
        Returns:
            LeafDescriptor
        """
        if isinstance(label_or_index, int):
            if label_or_index not in self._leaf_by_index:
                raise KeyError(f"No leaf at index {label_or_index}")
            return self._leaf_by_index[label_or_index]
        else:
            if label_or_index not in self._leaf_descriptors:
                raise KeyError(f"No leaf with label '{label_or_index}'")
            return self._leaf_descriptors[label_or_index]
    
    def control_block(self, label_or_index: Union[str, int]) -> str:
        """
        Get ControlBlock hex for a leaf.
        
        Args:
            label_or_index: Leaf label or index
            
        Returns:
            ControlBlock as hex string
        """
        from bitcoinutils.utils import ControlBlock
        
        leaf = self.leaf(label_or_index)
        cb = ControlBlock(
            self._internal_key._internal_pub,
            self._tree,
            leaf.index,
            is_odd=self._addr_obj.is_odd()
        )
        return cb.to_hex()
    
    # ══════════════════════════════════════════════════════════════
    # Spending Entry Points
    # ══════════════════════════════════════════════════════════════
    
    def spend(self, label_or_index: Union[str, int]) -> "SpendBuilder":
        """
        Create a SpendBuilder for script-path spending.
        
        Args:
            label_or_index: Leaf label (recommended) or index
            
        Returns:
            SpendBuilder configured for this leaf
        """
        from ..spend.builder import SpendBuilder
        
        leaf = self.leaf(label_or_index)
        return SpendBuilder(program=self, leaf=leaf, is_keypath=False)
    
    def keypath(self) -> "SpendBuilder":
        """
        Create a SpendBuilder for key-path spending.
        
        Key-path spending uses only the internal key signature.
        Maximum privacy - no script information revealed.
        
        Returns:
            SpendBuilder configured for key-path
        """
        from ..spend.builder import SpendBuilder
        
        return SpendBuilder(program=self, leaf=None, is_keypath=True)
    
    # ══════════════════════════════════════════════════════════════
    # Visualization
    # ══════════════════════════════════════════════════════════════
    
    def visualize(self) -> str:
        """
        Return ASCII tree visualization.
        """
        if self.num_leaves == 0:
            return "TaprootProgram (key-path only, no scripts)"
        
        if self.num_leaves == 4:
            labels = self.leaves
            return f"""
        Merkle Root
       /            \\
   Branch0        Branch1
   /      \\       /      \\
[{labels[0]}]  [{labels[1]}] [{labels[2]}]  [{labels[3]}]
"""
        
        # Generic visualization
        return f"TaprootProgram(leaves={self.leaves})"
    
    def explain(self):
        """
        Get structured explanation of this program.
        """
        from ..explain.program import ProgramExplanation
        return ProgramExplanation(self)
    
    def __repr__(self) -> str:
        return f"TaprootProgram(address={self.address}, leaves={self.leaves})"