# The two techniques

Both demos rest on the same two building blocks. No formal proofs here — the constructions are
confirmed on chain, and the argument below is the plain-language mechanism.

## 1. Same-signature binding

`OP_CHECKSIGFROMSTACK` (CSFS) verifies `Schnorr_Verify(pubkey, message, signature)` for a triple
sourced entirely from the witness stack — so on its own, the spender controls the message; nothing
ties it to the real transaction. `OP_CHECKSIG` verifies the *same* shape but against the
**node-computed** tapscript sighash, which the spender cannot choose.

The construction uses **one** 64-byte Schnorr signature in **both** checks:

```
... reassemble preimage from witness chunks ...
... compute tagged hash of it ...
<pubkey> OP_CHECKSIGFROMSTACK OP_VERIFY     # CSFS: sig over the witness-supplied preimage
<pubkey> OP_CHECKSIG                        # CHECKSIG: same sig over the node's real sighash
```

If one signature passes both, the witness-supplied preimage must be **byte-identical** to the
node's real one. Why: a Schnorr signature is tied to a single message — making one signature verify
against two different byte-strings would require colliding the hashes involved (a SHA-256
collision), which is infeasible.

A point worth making explicit: this does **not** rely on the spender being unable to forge
signatures. The spender holds the key and can sign anything. What it cannot do is make *one*
signature stand for *two* different transactions.

> **The exam analogy.** The node holds the official answer sheet (the real preimage) and will not
> show it. The spender may submit its own answer sheet (the witness preimage). A single red pen —
> the one signature under one public key — grades both. If it marks both "correct," the two sheets
> must be character-for-character identical.

Once witness bytes are pinned to real bytes, Script can read transaction fields by reading bytes
from the witness.

## 2. Preimage decomposition (emulating the disabled OP_SUBSTR)

`OP_SUBSTR` was disabled in Bitcoin Script's early consolidation. Its function — extract a field at
a given position — is exactly what on-chain introspection needs. We recover it by composing
currently-available opcodes.

The tapscript signature-message preimage (BIP-341 common SigMsg + BIP-342 tapscript extension) is
**field-aligned and fixed-length** (212 bytes) in the canonical case (SIGHASH_DEFAULT, no annex):

| Offset | Len | Field |
|--------|-----|-------|
| 10 | 32 | `sha_prevouts` (demo 2) |
| 42 | 32 | `sha_amounts` |
| 74 | 32 | `sha_scriptpubkeys` |
| 106 | 32 | `sha_sequences` |
| 138 | 32 | `sha_outputs` (demo 1) |

To verify a specific field, the witness presents the preimage as separate chunks split at that
field's boundary. The script:

1. `OP_SIZE`-locks chunk boundaries (an attacker cannot shift the field left/right without changing
   a chunk's size);
2. `OP_EQUALVERIFY`s the target chunk against the hardcoded expected value;
3. `OP_CAT`-reassembles the chunks in order;
4. asserts the reassembled preimage is exactly 212 bytes (rules out length-extension/truncation and
   pins the canonical layout);
5. computes the tagged hash and runs same-signature binding (§1).

The additional non-push cost is ~`2k` opcodes (one `OP_SIZE` + one `OP_CAT` per chunk) for `k`
chunks. The same construction reads any contiguous field — `sha_outputs`, `sha_prevouts`,
`sha_amounts`, `sha_scriptpubkeys`, etc. — by adjusting the chunking. That is the read capability a
dedicated introspection opcode (TXHASH-style) would provide, without activating one.
