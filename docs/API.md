# btcaaron API reference

Generated from the docstrings of btcaaron 0.3.0 (`tools/gen_api.py`). Everything listed is importable from the top-level `btcaaron` package unless a module path is shown.

## Keys

### `class Key(private_key: bitcoinutils.keys.PrivateKey)`

Bitcoin Key Manager (Immutable)

- `from_hex(hex_privkey: str) -> 'Key'`: Create Key from hex-encoded private key.
- `from_tprv(tprv: str, *, branch: int = 0, index: int = 0, purpose: int = 86, coin_type: Optional[int] = None, account: int = 0, network: str = 'testnet') -> 'Key'`: Create Key by deriving child private key from xpriv/tprv.
- `from_wif(wif: str) -> 'Key'`: Create Key from WIF (Wallet Import Format) string.
- `generate(network: str = 'testnet') -> 'Key'`: Generate a new random key.
- `pubkey` (property): 33-byte compressed public key (hex)
- `sign_taproot_script_bip118(self, tx, txin_index: int, utxo_scripts: list, amounts: list[int], tapleaf_script, hash_type: int = 65, annex: bytes | None = None) -> str`: Tapscript signature using BIP118 ``Msg118`` / ``Ext118`` (e.g. ``hash_type=0x41``).
- `wif` (property): WIF-encoded private key
- `xonly` (property): 32-byte x-only public key for Taproot (hex)

### `derive_wif_from_tprv(tprv: str, *, branch: int = 0, index: int = 0, purpose: int = 86, coin_type: Optional[int] = None, account: int = 0, network: str = 'testnet') -> str`

Derive a compressed child WIF from an account-level xpriv/tprv.

### `taproot_descriptor_from_tprv(tprv: str, *, branch: int = 0, purpose: int = 86, coin_type: Optional[int] = None, account: int = 0, network: str = 'testnet', wildcard: bool = True, index: int = 0) -> str`

Build a BIP86-style taproot descriptor string from xpriv/tprv.

### `wif_secret_bytes(wif: str) -> bytes`

Decode WIF and return 32-byte raw private key bytes.

## Taproot trees and programs

### `class TapTree(internal_key: btcaaron.key.Key, network: str = 'testnet')`

Taproot Script Tree Builder (Mutable)

- `bip118_checksig(self, key: btcaaron.key.Key, *, label: str = None) -> 'TapTree'`: Add a BIP118 (SIGHASH_ANYPREVOUT) script-path leaf.
- `build(self) -> btcaaron.tree.program.TaprootProgram`: Freeze the tree and create a TaprootProgram.
- `checksig(self, key: btcaaron.key.Key, *, label: str = None) -> 'TapTree'`: Add a single signature leaf.
- `custom(self, script: Union[ForwardRef('Script'), ForwardRef('RawScript')], *, label: str, unlock_hint: str = None, leaf_version: int = 192) -> 'TapTree'`: Add a custom script leaf.
- `hashlock(self, preimage: str, *, label: str = None) -> 'TapTree'`: Add a SHA256 hash lock leaf.
- `inscription(self, key: btcaaron.key.Key, body: Union[str, bytes], *, label: str = None, content_type: str = 'text/plain;charset=utf-8', protocol: str = 'ord') -> 'TapTree'`: Add a standard Ordinals-style inscription leaf.
- `multisig(self, threshold: int, keys: List[btcaaron.key.Key], *, label: str = None) -> 'TapTree'`: Add an N-of-M multisig leaf (Tapscript style with CHECKSIGADD).
- `timelock(self, *, blocks: int = None, timestamp: int = None, then: btcaaron.key.Key, label: str = None) -> 'TapTree'`: Add a CSV (relative) timelock leaf.

### `class TaprootProgram(internal_key: btcaaron.key.Key, leaves: List[dict], network: str)`

Frozen Taproot Script Tree (Immutable)

- `address` (property): Bech32m P2TR address of this program for its network.
- `control_block(self, label_or_index: Union[str, int]) -> str`: Control block (hex) proving the given leaf's membership in the tree (BIP 341).
- `explain(self)`: Structured explanation of the program (keys, leaves, scripts, address derivation).
- `internal_key` (property): x-only internal key (hex) before the Taproot tweak.
- `keypath(self) -> 'SpendBuilder'`: Start a key-path spend; returns a SpendBuilder.
- `leaf(self, label_or_index: Union[str, int]) -> btcaaron.tree.leaf.LeafDescriptor`: Return the LeafDescriptor for a leaf label or index (KeyError if absent).
- `leaves` (property): Leaf labels in tree order.
- `merkle_root` (property): Script-tree Merkle root (hex), or None for a key-path-only program.
- `merkle_root_bytes(self) -> bytes`: Return 32-byte merkle root for PSBT (BIP 371). Key-path with no tree: 32 zero bytes. Script-path or key-path with tree: computed root.
- `network` (property): Normalized network label: mainnet | testnet | regtest.
- `num_leaves` (property): Number of script leaves (0 for a key-path-only program).
- `spend(self, label_or_index: Union[str, int]) -> 'SpendBuilder'`: Start a script-path spend of the given leaf; returns a SpendBuilder.
- `spend_per_input(self, labels: Sequence[Union[str, int]]) -> 'SpendBuilder'`: Script-path spend with a different leaf per input (e.g. BIP119 n_in per index).
- `visualize(self) -> str`: ASCII drawing of the script tree with leaf labels.

### `class LeafDescriptor(label: str, index: int, script_type: Literal['HASHLOCK', 'CHECKSIG', 'BIP118_CHECKSIG', 'INSCRIPTION', 'MULTISIG', 'CSV_TIMELOCK', 'CLTV_TIMELOCK', 'CUSTOM'], script_hex: str, script_asm: str, params: Dict[str, Any], tapleaf_hash: str) -> None`

Immutable metadata for a Taproot script leaf.


### `LEAF_VERSION` = `192`

### `LEAF_VERSION_TAPSCRIPT_V2` = `194`

## Spending

### `class SpendBuilder(program: 'TaprootProgram', leaf: Optional[ForwardRef('LeafDescriptor')], is_keypath: bool, leaves: Optional[Sequence[ForwardRef('LeafDescriptor')]] = None)`

Transaction Spend Builder (Mutable)

- `add_external_input(self, txid: str, vout: int, sats: int, *, script_pubkey_hex: str, sign_keypath: Optional[btcaaron.key.Key] = None, keypath_tweak=None) -> 'SpendBuilder'`: Append an input from a different address (not this program's P2TR).
- `build(self) -> btcaaron.spend.transaction.Transaction`: Build the final transaction.
- `from_utxo(self, txid: str, vout: int = None, *, sats: int) -> 'SpendBuilder'`: Specify a single input UTXO.
- `from_utxos(self, utxos: List[Tuple[str, int, int]]) -> 'SpendBuilder'`: Specify multiple input UTXOs.
- `sequence(self, value: int) -> 'SpendBuilder'`: Set custom nSequence value for the input.
- `sign(self, *keys: btcaaron.key.Key) -> 'SpendBuilder'`: Provide signing keys.
- `to(self, address: str, sats: int) -> 'SpendBuilder'`: Add an output.
- `to_psbt(self)`: Build unsigned transaction as PSBT for multi-party signing.
- `to_psbt_v2(self)`: Build unsigned transaction as PSBT v2 (BIP 370) for multi-party signing.
- `unlock(self, *, preimage: str = None, **kwargs) -> 'SpendBuilder'`: Provide unlock data (for non-signature scripts like HASHLOCK).
- `unlock_with(self, witness_elements: List[str]) -> 'SpendBuilder'`: Manually provide witness stack (for CUSTOM scripts).

### `class Transaction(bu_tx: 'BUTransaction', program: 'TaprootProgram', leaf: Optional[ForwardRef('LeafDescriptor')], input_sats: int)`

Built Transaction (Immutable)

- `broadcast(self, *, provider: str = 'auto', explain: bool = False, allow_mainnet: bool = False, dry_run: bool = False) -> str`: Broadcast transaction to the network.
- `broadcast_plan(self, provider: str = 'auto') -> Dict[str, object]`: Return a side-effect-free plan for broadcast routing.
- `explain(self) -> 'TransactionExplanation'`: Get structured explanation of this transaction.
- `fee` (property): Transaction fee in satoshis
- `fee_rate` (property): Fee rate in sat/vB
- `hex` (property): Raw transaction hex
- `size` (property): Transaction size in bytes
- `txid` (property): Transaction ID (little-endian hex)
- `vsize` (property): Virtual size in vbytes

## Scripts and templates

### `class Script(bu_script)`

Bitcoin Script wrapper.

- `from_asm(asm: str) -> 'Script'`: Create script from ASM string.
- `from_hex(hex_str: str) -> 'Script'`: Create script from hex string.
- `from_ops(ops: List[str]) -> 'Script'`: Create script from list of operations.
- `to_asm(self) -> str`: Get script as ASM string.
- `to_hex(self) -> str`: Get script as hex string.

### `class RawScript(hex_str: str)`

Raw script wrapper that does NOT use bitcoin-utils parsing.

- `to_asm(self) -> str`: Simple display as hex (no parsing - use for RawScript).
- `to_bytes(self) -> bytes`: Get script as raw bytes.
- `to_hex(self) -> str`: Get script as hex string.

### `ord_inscription_script(signer: Union[btcaaron.key.Key, str], payload: Union[str, bytes, Mapping[str, Any]], *, content_type: str = 'text/plain;charset=utf-8', protocol: str = 'ord') -> btcaaron.script.script.Script`

Build an Ordinals-style inscription envelope tapscript.

### `brc20_mint_json(tick: str, amt: Union[str, int]) -> str`

Build canonical BRC-20 mint JSON payload.

## Bitcoin Inquisition templates

### `inq_cat_hashlock_script(expected_hash: Union[bytes, str]) -> btcaaron.script.script.RawScript`

Build Inquisition OP_CAT hashlock leaf script.

### `inq_csfs_script() -> btcaaron.script.script.RawScript`

Build Inquisition OP_CHECKSIGFROMSTACK leaf script.

### `inq_ctv_script(template_hash: Union[bytes, str]) -> btcaaron.script.script.RawScript`

Build Inquisition OP_CHECKTEMPLATEVERIFY leaf script.

### `inq_ctv_template_hash_for_output(output_sats: int, output_script_pubkey: Union[bytes, str], *, n_version: int = 2, n_locktime: int = 0, n_vin: int = 1, sequence: int = 4294967295, n_vout: int = 1, n_in: int = 0) -> bytes`

Compute CTV template hash for a single-output template.

### `inq_ctv_template_hash_for_outputs(outputs: Sequence[Tuple[int, Union[bytes, str]]], *, n_version: int = 2, n_locktime: int = 0, n_vin: int = 1, sequence: int = 4294967295, n_in: int = 0) -> bytes`

Compute CTV (BIP119-style) template hash for a multi-output template.

### `inq_ctv_program_for_output(internal_key: btcaaron.key.Key, output_sats: int, output_script_pubkey: Union[bytes, str], *, network: str = 'signet', label: str = 'ctv', sequence: int = 4294967295)`

Build a TapTree program that commits to a single-output CTV template.

### `inq_ctv_program_for_outputs(internal_key: btcaaron.key.Key, outputs: Sequence[Tuple[int, Union[bytes, str]]], *, network: str = 'signet', label: str = 'ctv', sequence: int = 4294967295)`

TapTree with one CTV leaf committing to a **multi-output** template (UHPO-style splits).

### `inq_apo_checksig_script(signer: Union[btcaaron.key.Key, str]) -> btcaaron.script.script.RawScript`

BIP118 tapscript leaf for ``SIGHASH_ANYPREVOUT`` script-path spends.

### `inq_apo_program(apo_signer: btcaaron.key.Key, *, internal_key: Optional[btcaaron.key.Key] = None, network: str = 'signet', label: str = 'apo')`

Single-leaf Taproot program: BIP118 ``<0x01||xonly> OP_CHECKSIG``.

### `inq_internalkey_equal_script(internal_key: Union[btcaaron.key.Key, str, bytes]) -> btcaaron.script.script.RawScript`

Tapscript leaf: ``OP_INTERNALKEY <32-byte x-only pubkey> OP_EQUAL``.

### `inq_internalkey_csfs_script() -> btcaaron.script.script.RawScript`

Tapscript leaf: ``OP_INTERNALKEY OP_CHECKSIGFROMSTACK`` (BIP 349 + CSFS).

### `inq_internalkey_equal_program(key: btcaaron.key.Key, *, network: str = 'signet', label: str = 'internalkey', unlock_hint: Optional[str] = 'OP_INTERNALKEY <xonly> OP_EQUAL')`

Single-leaf Taproot program: ``inq_internalkey_equal_script(key)``.

### `inq_internalkey_csfs_program(key: btcaaron.key.Key, *, network: str = 'signet', label: str = 'ik_csfs', unlock_hint: str = 'OP_INTERNALKEY OP_CHECKSIGFROMSTACK')`

Single-leaf Taproot program: ``inq_internalkey_csfs_script()``.

## Signature messages (BIP 341 / BIP 118)

### `compute_sigmsg_preimage(tx: 'Transaction', txin_index: 'int', script_pubkeys: 'Sequence[Script]', amounts: 'Sequence[int]', *, ext_flag: 'int' = 0, script: 'Optional[Script]' = None, leaf_ver: 'int' = 192, sighash: 'int' = 0) -> 'bytes'`

Build the BIP 341 SigMsg preimage (the data before ``TaggedHash``).

### `compute_sigmsg_digest(tx: 'Transaction', txin_index: 'int', script_pubkeys: 'Sequence[Script]', amounts: 'Sequence[int]', **kwargs) -> 'bytes'`

Compute the 32-byte TapSighash digest from the raw preimage.

### `bip118_sighash(tx: 'Transaction', txin_index: 'int', script_pubkeys: 'Sequence[Script]', amounts: 'Sequence[int]', tapleaf_script: 'Script', hash_type: 'int' = 65, annex: 'Optional[bytes]' = None) -> 'bytes'`

32-byte digest passed to BIP340 ``Verify`` for a BIP118 script-path signature.

### `apo_pubkey_bytes(xonly_32: 'bytes') -> 'bytes'`

33-byte BIP118 pubkey pushed before OP_CHECKSIG: ``0x01 || xonly``.

### `SIGHASH_ANYPREVOUT` = `64`

### `SIGHASH_ANYPREVOUTANYSCRIPT` = `192`

### `SIGHASH_DEFAULT_APO` = `65`

## PSBT (BIP 174 / 370 / 371)

### `class Psbt(tx)`

Partially Signed Bitcoin Transaction (BIP 174 + BIP 371 Taproot).

- `extract_transaction(self)`: Return the finalized transaction.
- `finalize(self) -> None`: Build final witnesses.
- `from_base64(b64: str) -> 'Psbt'`: Decode PSBT from base64 string.
- `sign_with(self, key: 'Key', input_index: int = 0) -> None`: Add Taproot signature for input.
- `to_base64(self) -> str`: Encode PSBT to base64.
- `to_v2(self) -> 'PsbtV2'`: Convert v0 PSBT to v2 (BIP 370) format.

### `class PsbtInput()`

Per-input PSBT data (Taproot).


### `class PsbtV2()`

PSBT Version 2 (BIP 370).

- `add_input(self, prev_txid: str, output_index: int, amount_sats: int, script_pubkey: bytes, *, sequence: int = 4294967295, tap_internal_key: Optional[bytes] = None, tap_merkle_root: Optional[bytes] = None, tap_leaf_script: Optional[Tuple[bytes, bytes]] = None, _tapleaf_script_obj=None, _tapleaf_scripts_for_tweak=None) -> 'PsbtV2'`: Add an input (incremental construction). prev_txid: 64-char hex; amount_sats > 0; script_pubkey: raw bytes.
- `add_output(self, amount_sats: int, script_pubkey: bytes) -> 'PsbtV2'`: Add an output (incremental construction). amount_sats > 0; script_pubkey: raw bytes.
- `extract_transaction(self)`: Assemble bitcoinutils Transaction from v2 maps.
- `finalize(self) -> None`: Build final witnesses (same logic as Psbt.finalize).
- `from_base64(b64: str) -> 'PsbtV2'`: Decode PSBT v2 from base64.
- `from_psbt_v0(psbt: btcaaron.psbt.Psbt) -> 'PsbtV2'`: Create PsbtV2 from a v0 Psbt.
- `from_v0_base64(b64: str) -> 'PsbtV2'`: Parse v0 PSBT from base64, return as PsbtV2. For interop with v0-only tools.
- `sign_with(self, key: 'Key', input_index: int = 0) -> None`: Add Taproot signature for input (same logic as Psbt.sign_with).
- `to_base64(self) -> str`: Encode PSBT v2 to base64.

### `class PsbtV2Input()`

Per-input PSBT v2 data: tx fields + BIP 371 Taproot.


## Node RPC helpers

### `broadcast_tx_hex(rpc: 'RpcFn', tx_hex: 'str') -> 'str'`

Broadcast raw tx hex and return txid.

### `find_utxo_for_address(rpc: 'RpcFn', address: 'str', txid_hint: 'Optional[str]' = None) -> 'Optional[Utxo]'`

Find one UTXO paying to `address`.

### `sats_from_rpc_amount(value: 'Any') -> 'int'`

Convert RPC amount field to satoshis.

### `wallet_change_address(rpc_wallet: 'RpcFn') -> 'str'`

Get a bech32m change address from wallet RPC.

### `wallet_send_sats(rpc_wallet: 'RpcFn', address: 'str', sats: 'int') -> 'str'`

Send sats to an address via wallet RPC and return txid.

## Errors

### `class BtcAaronError`

Base exception for btcaaron


### `class BuildError`

Transaction/Tree building errors


### `class BroadcastError`

Network broadcast errors


### `class ValidationError`

Validation errors


## Legacy v0.1 API

### `class WIFKey(wif_str: str)`

WIF Private Key Manager

- `get_legacy(self) -> 'BTCAddress'`: Get Legacy address object (P2PKH)
- `get_segwit(self) -> 'BTCAddress'`: Get SegWit address object (P2WPKH)
- `get_taproot(self) -> 'BTCAddress'`: Get Taproot address object (P2TR)

### `class BTCAddress(wif: str, address: str, addr_type: str, private_key, public_key)`

Bitcoin Address Handler

- `get_balance(self, debug: bool = False) -> int`: Get address balance
- `scan_utxos(self, debug: bool = False) -> List[Dict]`: Scan all available UTXOs for this address
- `send(self, to_addr: str, amount: int, fee: int = 300, debug: bool = False) -> 'BTCTransaction'`: Create and sign a transfer transaction

### `class BTCTransaction(tx_hex: str, debug: bool = False)`

Bitcoin Transaction Handler

- `broadcast(self) -> Optional[str]`: Broadcast transaction to network

### `wif_to_addresses(wif: str) -> Dict[str, str]`

Generate all address types from WIF

### `quick_transfer(wif: str, from_type: str, to_addr: str, amount: int, fee: int = 300, debug: bool = False) -> Optional[str]`

Quick transfer using specified address type.

### `quick_transfer_tprv(tprv: str, to_addr: str, amount: int, *, fee: int = 300, branch: int = 0, index: int = 0, purpose: int = 86, coin_type: Optional[int] = None, account: int = 0, network: str = 'testnet', debug: bool = False) -> Optional[str]`

One-liner helper: derive taproot key from tprv/xpriv and send sats.

### `taproot_balance_from_tprv(tprv: str, *, branch: int = 0, index: int = 0, purpose: int = 86, coin_type: Optional[int] = None, account: int = 0, network: str = 'testnet', debug: bool = False) -> int`

One-liner helper: derive taproot key from tprv/xpriv and query balance.

### `fund_program(wif: str, program: 'TaprootProgram', amount: int, fee: int = 300, debug: bool = False) -> Optional[str]`

Fund a Taproot commit address from your taproot wallet.

## BIP 446 template hash (`btcaaron.templatehash`)

### `sha_outputs(outputs: 'Sequence[Tuple[int, bytes]]') -> 'bytes'`

BIP341 sha_outputs: SHA256 of all outputs in CTxOut format (amount || compact_size || spk).

### `sha_sequences(sequences: 'Sequence[int]') -> 'bytes'`

BIP341 sha_sequences: SHA256 of all input nSequence values (4-byte LE each).

### `tagged_hash(tag: 'str', msg: 'bytes') -> 'bytes'`

_No docstring._

### `template_hash(version: 'int', locktime: 'int', sequences: 'Sequence[int]', outputs: 'Sequence[Tuple[int, bytes]]', input_index: 'int' = 0, annex: 'Optional[bytes]' = None) -> 'bytes'`

32-byte value OP_TEMPLATEHASH pushes for this (version, locktime, sequences, outputs, index).

### `template_msg(version: 'int', locktime: 'int', sequences: 'Sequence[int]', outputs: 'Sequence[Tuple[int, bytes]]', input_index: 'int' = 0, annex: 'Optional[bytes]' = None) -> 'bytes'`

The pre-image that OP_TEMPLATEHASH hashes (72 bytes + 5, or + 37 with an annex).

