# Demo 2 — Input binding (beyond CTV's template)

Confirmed: [b7959a71…304606](https://mempool.space/signet/tx/b7959a71b74b8bbed69d52c22a9b3b90af176391be2d0b7f33eb1a6473304606) and
[7311da6e…a83558](https://mempool.space/signet/tx/7311da6e30886fab6594b633bcb97e4436d49f02ecc244d4bc7c59cb1ea83558) (Inquisition signet).

`OP_CHECKTEMPLATEVERIFY` commits to *outputs* but **not** to inputs — `sha_prevouts` is not a field
of CTV's template. Some applications need to enforce that a spending transaction consumes a
specific UTXO (or set of UTXOs); CTV alone cannot. CSFS+CAT can: it is the **same construction as
[demo 1](output_binding.md)** — only the chunk position and the expected value change.

## Construction

Using the preimage-decomposition + same-signature-binding technique, we extract `sha_prevouts`
(preimage bytes 10–41) instead of `sha_outputs`. The 196-byte leaf of A hardcodes **B's outpoint**
(36 bytes); the witness supplies **A's outpoint**, and the script computes the expected hash on the
stack:

```
witness (bottom -> top): sig(64) post_c(56) post_b(57) post_a(57) pre(10) sha(32) a_outpoint(36)

<B_outpoint> CAT SHA256 SWAP DUP ROT EQUALVERIFY   # sha == SHA256(a_outpoint || B)
SWAP SIZE 10 EQUALVERIFY                            # pre is 10 bytes -> sha sits at offset 10
SWAP CAT SWAP CAT SWAP CAT SWAP CAT                 # pre||sha||post_a||post_b||post_c
<tag[0:32]> <tag[32:64]> CAT SWAP CAT SHA256        # TapSighash(preimage)
OVER SWAP <pk> CHECKSIGFROMSTACK VERIFY             # sig valid over witness preimage
<pk> CHECKSIG                                       # same sig valid over real sighash
```

| | |
|---|---|
| Goal | spend A only if a specific UTXO B is spent in the same transaction |
| Witness layout | 7 stack items: `[sig, post_c, post_b, post_a, pre, sha_prevouts, a_outpoint]`, then the 196-byte leaf and control block; every item < 80 bytes |
| Hardcoded in the leaf | B's outpoint (not a precomputed hash) |
| Enforcement target | `sha_prevouts` field at preimage byte offset 10 |
| Confirmed TXIDs | [b7959a71…304606](https://mempool.space/signet/tx/b7959a71b74b8bbed69d52c22a9b3b90af176391be2d0b7f33eb1a6473304606), [7311da6e…a83558](https://mempool.space/signet/tx/7311da6e30886fab6594b633bcb97e4436d49f02ecc244d4bc7c59cb1ea83558) |
| Negative test | A + C rejected by `testmempoolaccept`: `Script failed an OP_EQUALVERIFY operation` |

The spend is valid only if `SHA256(outpoint_A || outpoint_B)` equals the transaction's real
`sha_prevouts`, i.e. **"spend A only if B is co-spent."** If C is substituted for B, supplying the
real `SHA256(A || C)` fails the `EQUALVERIFY`; supplying `SHA256(A || B)` makes the witness
preimage differ from the real one, so the same signature cannot pass both CSFS and CHECKSIG.

Standalone code and a keyless on-chain verifier (it re-checks both transactions from
mempool.space): [aaron-recompile/sighash-prevout-binding](https://github.com/aaron-recompile/sighash-prevout-binding).

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
