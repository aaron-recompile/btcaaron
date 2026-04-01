# Bitcoin Inquisition (Experimental)

This page tracks experimental opcode templates for Bitcoin Inquisition signet.

Status:

- Implemented as reusable script helpers in `btcaaron.script.templates`
- Covered by unit tests in `tests/test_btcaaron_v02.py`
- Intended for research/testing workflows (not a mainnet policy claim)

## Scope

Currently included templates:

- `inq_cat_hashlock_script(expected_hash)` -> `OP_CAT OP_SHA256 <hash> OP_EQUAL`
- `inq_csfs_script()` -> `OP_CHECKSIGFROMSTACK`
- `inq_ctv_script(template_hash)` -> `<hash> OP_CHECKTEMPLATEVERIFY`
- `inq_apo_checksig_script(signer)` / `inq_apo_program(signer)` -> BIP118 `<0x01||x-only> OP_CHECKSIG` (needs BIP118 consensus, not relayed on vanilla nodes)

## Quick usage

```python
from btcaaron import (
    Key,
    TapTree,
    inq_cat_hashlock_script,
    inq_csfs_script,
    inq_ctv_script,
    inq_apo_program,
)

key = Key.from_wif("c...")  # signet/testnet WIF

cat_program = TapTree(internal_key=key, network="signet").custom(
    script=inq_cat_hashlock_script(bytes.fromhex("936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af")),
    label="cat",
).build()

# BIP118 (APO) single-leaf program — spend with .sign(key) on script path
apo_program = inq_apo_program(key, network="signet")
```

### BIP118 (ANYPREVOUT) notes

- Leaf pushes a **33-byte** “BIP118 pubkey” (`0x01` || 32-byte x-only), then `OP_CHECKSIG`. This is **not** the same as ordinary tapscript `<xonly> OP_CHECKSIG`.
- Signatures use **BIP118 sighash** (`Msg118`/`Ext118` + `TaggedHash("TapSighash", …)`); `Key.sign_taproot_script_bip118` appends the sighash byte (e.g. `0x41` = ALL|ANYPREVOUT).
- **Eltoo / channel binding** uses the property that the digest does not commit to the specific prevout when using ANYPREVOUT (see `tests/test_bip118.py`).

## Further reading

**Companion repo (binding-target experiments):** [bitcoin-signature-binding](https://github.com/aaron-recompile/bitcoin-signature-binding) — reproducible offline JSON + optional Signet scripts comparing message-bound CSFS, identity-bound internal-key+CSFS, and sighash-bound CHECKSIG.

**Signet / Inquisition blog series (Medium):**

- [OP_CAT on Signet — concatenation, commitment, Bitcoin Inquisition](https://medium.com/@aaron.recompile/op-cat-on-signet-concatenation-commitment-and-bitcoin-inquisition-ed34a07866d6)
- [OP_CHECKSIGFROMSTACK on Signet — sign anything, verify on stack](https://medium.com/@aaron.recompile/op-checksigfromstack-on-signet-sign-anything-verify-on-stack-9cf70ab07583)
- [OP_CHECKTEMPLATEVERIFY on Signet — locking outputs at UTXO creation time](https://medium.com/@aaron.recompile/op-checktemplateverify-on-signet-locking-outputs-at-utxo-creation-time-1d623fbe3899)
- [OP_INTERNALKEY + OP_CHECKSIGFROMSTACK on Signet — identity-bound authorization](https://medium.com/@aaron.recompile/op-internalkey-op-checksigfromstack-on-signet-identity-bound-authorization-04f0440557bc)

## Notes

- Transaction relay can differ from consensus acceptance on mixed peer sets.
- For Inquisition features, peer topology and miner reachability can affect `reveal -> confirm` latency.
- Keep experimental workflows isolated from production defaults.
