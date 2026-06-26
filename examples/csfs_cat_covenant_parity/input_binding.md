# Demo 2 — Input binding (beyond CTV's template)

Confirmed: [7311da6e…a83558](https://mempool.space/signet/tx/7311da6e30886fab6594b633bcb97e4436d49f02ecc244d4bc7c59cb1ea83558)
(Inquisition signet).

`OP_CHECKTEMPLATEVERIFY` commits to *outputs* but **not** to inputs — `sha_prevouts` is not a field
of CTV's template. Some applications need to enforce that a spending transaction consumes a
specific UTXO (or set of UTXOs); CTV alone cannot. CSFS+CAT can: it is the **same construction as
[demo 1](output_binding.md)** — only the chunk position and the expected value change.

## Construction

Using the preimage-decomposition + same-signature-binding technique, we extract `sha_prevouts`
(preimage bytes 10–41) instead of `sha_outputs`, and require it to equal a hardcoded value:

```
preimage chunks:  pre_a || sha_prevouts(32) || post
                            \
                         sha_prevouts == SHA256(serialized_outpoint_A || serialized_outpoint_B)
```

| | |
|---|---|
| Goal | force the spending transaction's input set to match a precommitted set of outpoints |
| Witness layout | `[sig, post, sha_prevouts, pre_a, pubkey]` |
| Enforcement target | `sha_prevouts` field at preimage byte offset 10 |
| Confirmed TXID | [7311da6e…a83558](https://mempool.space/signet/tx/7311da6e30886fab6594b633bcb97e4436d49f02ecc244d4bc7c59cb1ea83558) |
| Negative test | `testmempoolaccept` rejection when the input set is changed |

The expected value is hardcoded as `SHA256(serialized_outpoint_A || serialized_outpoint_B)`, so the
spend is valid only if the transaction's inputs hash to exactly that — i.e. **"spend A only if B is
co-spent."**

## Why this matters — the BitVM co-spend connector

This is a capability **neither CTV nor APO** provides. Robin Linus's BitVM-bridge construction
needs to bind an operator's on-chain step to a specific UTXO; ajtowns noted in the same thread that
CTV commits to a `scriptSig`'s *content* but not to *which UTXO it comes from*. Input binding
addresses this natively in tapscript by constraining `sha_prevouts` directly, regardless of how the
inputs are constructed.

It is on a different axis from CTV (output-only) and from APO (which *loosens* the prevout
commitment for rebinding) — input binding *tightens* it. So "beyond CTV" here means an off-axis
capability, not a strictly stronger version of CTV's output template.

Full construction (196-byte tapscript, hardcoded prevout, dynamic SHA256 reconstruction), witness
layout, and the failed-substitution record:
[Delving /t/2483](https://delvingbitcoin.org/t/taproot-native-prevout-binding-via-sighash-preimage-decomposition/2483).
