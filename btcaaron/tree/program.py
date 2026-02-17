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
    """
    
    def __init__(self, internal_key: Key, leaves: List[dict], network: str):
        self._internal_key = internal_key
        self._network = network
        self._raw_leaves = leaves
        
        self._leaf_descriptors: Dict[str, LeafDescriptor] = {}
        self._leaf_by_index: Dict[int, LeafDescriptor] = {}
        self._scripts = []
        self._address: Optional[str] = None
        self._merkle_root: Optional[str] = None
        
        self._compile()
    
    def _compile(self):
        """Compile leaves into scripts and compute Taproot address."""
        from bitcoinutils.script import Script as BUScript
        from bitcoinutils.transactions import Sequence
        from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK

        from ..script.script import RawScript

        scripts = []

        for leaf_data in self._raw_leaves:
            script_type = leaf_data["script_type"]
            params = leaf_data["params"]
            label = leaf_data["label"]
            index = leaf_data["index"]

            if script_type == "HASHLOCK":
                script = BUScript([
                    'OP_SHA256',
                    params["preimage_hash"],
                    'OP_EQUALVERIFY',
                    'OP_TRUE'
                ])

            elif script_type == "CHECKSIG":
                script = BUScript([
                    params["pubkey"],
                    'OP_CHECKSIG'
                ])

            elif script_type == "MULTISIG":
                ops = ["OP_0"]
                for pk in params["pubkeys"]:
                    ops.append(pk)
                    ops.append("OP_CHECKSIGADD")
                ops.append(f"OP_{params['threshold']}")
                ops.append("OP_EQUAL")
                script = BUScript(ops)

            elif script_type == "CSV_TIMELOCK":
                blocks = params.get("blocks") or params.get("sequence_value")
                seq = Sequence(TYPE_RELATIVE_TIMELOCK, blocks)
                script = BUScript([
                    seq.for_script(),
                    "OP_CHECKSEQUENCEVERIFY",
                    "OP_DROP",
                    params["pubkey"],
                    "OP_CHECKSIG"
                ])

            elif script_type == "CUSTOM":
                script = params["script"]
                if isinstance(script, RawScript):
                    script = script  # keep as RawScript
                else:
                    script = script._internal  # our Script -> bitcoinutils

            else:
                raise ValueError(f"Unknown script type: {script_type}")

            scripts.append(script)

            script_hex = script.to_hex()
            script_asm = script.to_asm() if isinstance(script, RawScript) else str(script)

            descriptor = LeafDescriptor(
                label=label,
                index=index,
                script_type=script_type,
                script_hex=script_hex,
                script_asm=script_asm,
                params=params,
                tapleaf_hash="",
            )

            self._leaf_descriptors[label] = descriptor
            self._leaf_by_index[index] = descriptor

        self._scripts = scripts

        # Check if any RawScript (has_raw) -> use tapmath path
        has_raw = any(isinstance(s, RawScript) for s in scripts)

        if has_raw:
            # Tapmath path: no bitcoinutils tree, use tagged hashes
            from . import tapmath

            def _script_to_bytes(s):
                if isinstance(s, RawScript):
                    return s.to_bytes()
                return bytes.fromhex(s.to_hex())

            script_bytes_list = [_script_to_bytes(s) for s in scripts]
            leaf_hashes = [tapmath.tapleaf_hash(b) for b in script_bytes_list]
            merkle_root = tapmath.compute_merkle_root(leaf_hashes)

            self._use_tapmath = True
            self._leaf_hashes = leaf_hashes
            self._merkle_root = merkle_root
            self._tree = None

            addr = self._internal_key._internal_pub.get_taproot_address(merkle_root)
            self._address = addr.to_string()
            self._addr_obj = addr
        else:
            # Original bitcoinutils path
            self._use_tapmath = False
            self._leaf_hashes = None
            self._merkle_root = None

            if len(scripts) == 0:
                tree = None
            else:
                tree = self._build_balanced_tree(scripts)

            self._tree = tree

            if tree is None:
                addr = self._internal_key._internal_pub.get_taproot_address()
            else:
                addr = self._internal_key._internal_pub.get_taproot_address(tree)

            self._address = addr.to_string()
            self._addr_obj = addr
    
    @staticmethod
    def _build_balanced_tree(scripts):
        """Build a balanced nested list for bitcoin-utils from a flat script list."""
        if len(scripts) == 1:
            return scripts[0]
        if len(scripts) == 2:
            return [scripts[0], scripts[1]]
        mid = len(scripts) // 2
        left = TaprootProgram._build_balanced_tree(scripts[:mid])
        right = TaprootProgram._build_balanced_tree(scripts[mid:])
        return [left, right]

    @property
    def address(self) -> str:
        return self._address
    
    @property
    def internal_key(self) -> str:
        return self._internal_key.xonly
    
    @property
    def merkle_root(self) -> Optional[str]:
        mr = self._merkle_root
        return mr.hex() if isinstance(mr, bytes) else mr
    
    @property
    def leaves(self) -> List[str]:
        sorted_leaves = sorted(self._leaf_descriptors.values(), key=lambda x: x.index)
        return [leaf.label for leaf in sorted_leaves]
    
    @property
    def num_leaves(self) -> int:
        return len(self._leaf_descriptors)
    
    def leaf(self, label_or_index: Union[str, int]) -> LeafDescriptor:
        if isinstance(label_or_index, int):
            if label_or_index not in self._leaf_by_index:
                raise KeyError(f"No leaf at index {label_or_index}")
            return self._leaf_by_index[label_or_index]
        else:
            if label_or_index not in self._leaf_descriptors:
                raise KeyError(f"No leaf with label '{label_or_index}'")
            return self._leaf_descriptors[label_or_index]
    
    def control_block(self, label_or_index: Union[str, int]) -> str:
        leaf = self.leaf(label_or_index)
        if getattr(self, '_use_tapmath', False):
            from . import tapmath
            internal_key_bytes = bytes.fromhex(self._internal_key.xonly)
            cb_bytes = tapmath.compute_control_block(
                internal_key_bytes,
                self._leaf_hashes,
                leaf.index,
                is_odd=self._addr_obj.is_odd(),
            )
            return cb_bytes.hex()
        else:
            from bitcoinutils.utils import ControlBlock
            cb = ControlBlock(
                self._internal_key._internal_pub,
                self._tree,
                leaf.index,
                is_odd=self._addr_obj.is_odd()
            )
            return cb.to_hex()
    
    def spend(self, label_or_index: Union[str, int]) -> "SpendBuilder":
        from ..spend.builder import SpendBuilder
        leaf = self.leaf(label_or_index)
        return SpendBuilder(program=self, leaf=leaf, is_keypath=False)
    
    def keypath(self) -> "SpendBuilder":
        from ..spend.builder import SpendBuilder
        return SpendBuilder(program=self, leaf=None, is_keypath=True)
    
    def visualize(self) -> str:
        if self.num_leaves == 0:
            return "TaprootProgram (key-path only, no scripts)"
        labels = self.leaves
        if self.num_leaves == 1:
            return f"""
  Taproot
    |
[{labels[0]}]
"""
        if self.num_leaves == 2:
            return f"""
    Merkle Root
   /            \\
[{labels[0]}]        [{labels[1]}]
"""
        if self.num_leaves == 4:
            return f"""
        Merkle Root
       /            \\
   Branch0        Branch1
   /      \\       /      \\
[{labels[0]}]  [{labels[1]}] [{labels[2]}]  [{labels[3]}]
"""
        return f"TaprootProgram(leaves={self.leaves})"
    
    def explain(self):
        from ..explain.program import ProgramExplanation
        return ProgramExplanation(self)
    
    def __repr__(self) -> str:
        return f"TaprootProgram(address={self.address}, leaves={self.leaves})"