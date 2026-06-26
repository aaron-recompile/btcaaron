# Demo 1 — Output binding (= CTV's output template), byte for byte

Confirmed: [2f345180…1f37e6](https://mempool.space/signet/tx/2f345180bc6654353a247a50559c0be42153707b2ca29b621e57671ed41f37e6)
(Inquisition signet, block 300379), spending a 50,000-sat UTXO created by
[05f9372d…2ca0cc](https://mempool.space/signet/tx/05f9372dff7184ad736373165bc617ba100315bd2c187b0a4c893d796b2ca0cc):1.

This forces the spending transaction's `sha_outputs` to a hardcoded value — the same enforced
relation CTV provides — using only CSFS + CAT. Everything below is checkable against the
confirmed witness on the explorer.

## Hardcoded values in the tapleaf

| Constant | Value | Role |
|----------|-------|------|
| Expected `sha_outputs` | `eb0fdcd005abb92861dfa7c7680c8a7b417e75c62c823b425615a0bee9082d7d` | the enforced 32-byte output template (preimage offset 138) |
| `pubkey` (x-only) | `ff1f9f…86b8` | key for both CSFS and CHECKSIG |
| `SHA256("TapSighash")` | `f40a48df4b2a70c8b4924bf2654661ed3d95fd66a313eb87237597c628e4a031` | pushed twice and `OP_CAT`-ed into the 64-byte BIP-340 tag prefix |

## Witness layout (top to bottom)

```
[ sig_64, post(42), sha_outputs(32), pre_c(46), pre_b(46), pre_a(46), control_block ]
```

Each item is ≤ 80 bytes (Inquisition standardness). The five preimage chunks partition the
212-byte tapscript signature-message preimage at byte offsets `[0,46) [46,92) [92,138)
[138,170) [170,212)`; only the fourth chunk coincides with a BIP-341 field boundary
(`sha_outputs`, bytes 138–169). The `pre_*` chunks are length-driven padding, not field-aligned.

## Annotated tapscript ASM (the actual witness script of the spend)

```
OP_SWAP                            (1) bring the sha_outputs chunk to the top
OP_DUP                             (2) duplicate it
OP_PUSHBYTES_32 eb0fdcd0...082d7d  (3) push the expected sha_outputs
OP_EQUALVERIFY                     (4) require: witness sha_outputs == expected  (template)
OP_ROT                             (5) rotate pre_c up
OP_SIZE
OP_PUSHBYTES_1 2e                  (6) push 0x2e = 46
OP_EQUALVERIFY                     (7) require: |pre_c| == 46   (boundary lock)
OP_SWAP / OP_CAT x4                (8) CAT-reassemble 5 chunks -> 212-byte preimage
OP_PUSHBYTES_32 f40a48df...4a031   (9) push SHA256("TapSighash")  (tag, upper)
OP_PUSHBYTES_32 f40a48df...4a031   (10) push SHA256("TapSighash")  (tag, lower, identical)
OP_CAT                             (11) form the 64-byte tag prefix
OP_SWAP
OP_CAT                             (12) tag_prefix || preimage   (64 + 212 = 276 bytes)
OP_SHA256                          (13) -> witness_SigMsg (32 bytes)
OP_OVER / OP_SWAP                  (14) bring sig up
OP_PUSHBYTES_32 ff1f9f...86b8      (15) push pubkey
OP_CHECKSIGFROMSTACK               (16) (OP_SUCCESS_204) verify sig over witness_SigMsg
OP_VERIFY                          (17) CSFS must return 1
OP_PUSHBYTES_32 ff1f9f...86b8      (18) push the same pubkey
OP_CHECKSIG                        (19) verify the same sig over the node-computed SigMsg
```

Step (4) enforces the template; steps (16) and (19) are the two arms of same-signature binding
(see [`techniques.md`](techniques.md)). Because one signature cannot pass for two different
preimages, (16) + (19) on a single `sig` force the reassembled 212-byte witness preimage to equal
the node's real preimage; step (4) then pins the real `sha_outputs` to the hardcoded value.

## Why a boundary shift fails

A spender wanting to send funds elsewhere might misalign the chunks — e.g. make `pre_a` 47 bytes
so the fourth chunk reads preimage bytes `[137,169)` instead of `[138,170)`, hoping (4) still
matches. For (4) to pass, the shifted slice would have to equal the hardcoded constant; for
(16)+(19) to pass, the reassembled preimage must still equal the real one. Concretely the attacker
would need a transaction whose real preimage has `preimage[137]=0xeb` and `preimage[138..169]`
equal to the first 31 bytes of the constant — forcing a SHA-256 image (`sha_outputs`) to match a
**fixed** 248-bit target. With a fixed target there is no birthday shortcut; this is a
second-preimage-style search far beyond any feasible work (well past 2^128). The single `OP_SIZE`
lock at (7) is a belt-and-suspenders boundary pin; the cryptographic anchor is (4)+(16)+(19).

**Negative test.** Re-running the spend with an output to a different address, all else fixed, is
rejected by `testmempoolaccept` with an `OP_EQUALVERIFY` failure at step (4) — the on-chain
analogue of a CTV template-mismatch rejection. Full step-by-step stack trace:
[Delving /t/2483/3](https://delvingbitcoin.org/t/taproot-native-prevout-binding-via-sighash-preimage-decomposition/2483/3).
