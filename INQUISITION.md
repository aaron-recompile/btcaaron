# Bitcoin Inquisition (Experimental)

This page tracks experimental opcode templates for Bitcoin Inquisition signet.


Status:

- Implemented as reusable script helpers in `btcaaron.script.templates`
- Covered by unit tests in `tests/test_btcaaron_v02.py`
- Intended for research/testing workflows (not a mainnet policy claim)

## Scope

**Helpers in `btcaaron.script.templates`:**

| Helper | Role |
|--------|------|
| `inq_cat_hashlock_script(expected_hash)` | `OP_CAT` + hash preimage check |
| `inq_csfs_script()` | `OP_CHECKSIGFROMSTACK` |
| `inq_ctv_script(template_hash)` | `OP_CHECKTEMPLATEVERIFY` (template hash on stack) |
| `inq_apo_checksig_script` / `inq_apo_program` | Tapscript leaf for **BIP118** ANYPREVOUT spends (`0x01‖x-only` + `OP_CHECKSIG`, not ordinary BIP342 tapscript `CHECKSIG`). Enables Eltoo-style state updates without committing to a specific prevout. |
| `inq_internalkey_equal_script` / `inq_internalkey_equal_program` | `OP_INTERNALKEY` + `<xonly>` + `OP_EQUAL` |
| `inq_internalkey_csfs_script` / `inq_internalkey_csfs_program` | `OP_INTERNALKEY` + `OP_CHECKSIGFROMSTACK` |


## Quick usage

```python
from btcaaron import (
    Key,
    TapTree,
    inq_cat_hashlock_script,
    inq_csfs_script,
    inq_ctv_script,
    inq_apo_program,
    inq_internalkey_equal_program,
    inq_internalkey_csfs_program,
)

key = Key.from_wif("c...")  # signet/testnet WIF

cat_program = TapTree(internal_key=key, network="signet").custom(
    script=inq_cat_hashlock_script(bytes.fromhex("936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af")),
    label="cat",
).build()

apo_program = inq_apo_program(key, network="signet")
```


## Further reading

**Companion repo (binding experiments):** [bitcoin-signature-binding](https://github.com/aaron-recompile/bitcoin-signature-binding) — offline JSON + Signet scripts comparing CSFS, IK+CSFS, and ordinary `CHECKSIG` binding.

**Signet / Inquisition (Medium):**

- [OP_CAT on Signet — concatenation, commitment, Bitcoin Inquisition](https://medium.com/@aaron.recompile/op-cat-on-signet-concatenation-commitment-and-bitcoin-inquisition-ed34a07866d6)
- [OP_CHECKSIGFROMSTACK on Signet — sign anything, verify on stack](https://medium.com/@aaron.recompile/op-checksigfromstack-on-signet-sign-anything-verify-on-stack-9cf70ab07583)
- [OP_CHECKTEMPLATEVERIFY on Signet — locking outputs at UTXO creation time](https://medium.com/@aaron.recompile/op-checktemplateverify-on-signet-locking-outputs-at-utxo-creation-time-1d623fbe3899)
- [OP_INTERNALKEY + OP_CHECKSIGFROMSTACK on Signet — identity-bound authorization](https://medium.com/@aaron.recompile/op-internalkey-op-checksigfromstack-on-signet-identity-bound-authorization-04f0440557bc)
- [OP_CAT + OP_CHECKSIGFROMSTACK on Signet — dynamic message, oracle authorization](https://medium.com/@aaron.recompile/op-cat-op-checksigfromstack-on-signet-dynamic-message-oracle-authorization-8c73e1ef5353)

**Delving Bitcoin (threads):**

- [Bitcoin Inquisition 29.2 (release / consensus features)](https://delvingbitcoin.org/t/bitcoin-inqusition-29-2/2236)
- [What exactly is bound in CSFS, IK+CSFS, and CHECKSIG?](https://delvingbitcoin.org/t/what-exactly-is-bound-in-csfs-ik-csfs-and-checksig/2351)

## Notes

- Transaction relay can differ from consensus acceptance on mixed peer sets.
- For Inquisition features, peer topology and miner reachability can affect `reveal -> confirm` latency.
- Keep experimental workflows isolated from production defaults.
