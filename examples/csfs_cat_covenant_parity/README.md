# CSFS+CAT covenant parity — on-chain reproduction package

Reproduction material for **"Capability Parity of CSFS+CAT with CTV and ANYPREVOUT
for Common Covenant Patterns: On-Chain Evidence from Inquisition Signet"** (A. Zhang).

The claim is empirical and bounded: using only **already-activated** Inquisition opcodes
— `OP_CHECKSIGFROMSTACK` (BIP-348) and `OP_CAT` (BIP-347) — we reproduce, on chain, the
covenant capabilities of `OP_CHECKTEMPLATEVERIFY` (CTV) and BIP-118 ANYPREVOUT for three
common patterns, **for spends where the spending signer participates**. We do not claim
sufficiency for every covenant, nor that CSFS+CAT should replace either opcode as a
deployment optimization.

Everything here is **public data** — every construction is verifiable from its confirmed
witness on a block explorer; no private keys are included or required.

## Reviewers start here — three confirmed Inquisition-signet spends

| # | Pattern | What it shows | Confirmed TXID |
|---|---------|---------------|----------------|
| 1 | **Output binding** (= CTV's output template) | forces `sha_outputs` to a hardcoded value | [2f345180…1f37e6](https://mempool.space/signet/tx/2f345180bc6654353a247a50559c0be42153707b2ca29b621e57671ed41f37e6) (block 300379) |
| 2 | **Input binding** (beyond CTV's template) | forces a specific `sha_prevouts` — "spend A only if B is co-spent" | [7311da6e…a83558](https://mempool.space/signet/tx/7311da6e30886fab6594b633bcb97e4436d49f02ecc244d4bc7c59cb1ea83558) |
| 3 | **Eltoo state replacement** (APO's use-case, via a CSFS+CTV ladder) | reaches eltoo's topology — O(n) delegation, *not* APO's O(1) rebinding | fund [92efc475…1fda34](https://mempool.space/signet/tx/92efc47554d25d74d9f567594d37375d8c8a1a2ea6bd1864600d5a49531fda34) → settle [b96324da…8382de](https://mempool.space/signet/tx/b96324da612950339f564fbc88fe1d5c5751070e57bf796d32ee7171238382de) |

Demo 1's UTXO was created by [05f9372d…2ca0cc](https://mempool.space/signet/tx/05f9372dff7184ad736373165bc617ba100315bd2c187b0a4c893d796b2ca0cc):1 (50,000 sat).

## The two techniques behind all three

1. **Same-signature binding** — one Schnorr signature must satisfy *both* `OP_CHECKSIG`
   (against the node-computed sighash) *and* `OP_CHECKSIGFROMSTACK` (against a witness-supplied
   preimage). Because one signature cannot stand for two different messages, the witness preimage
   is forced to be byte-identical to the node's real one — so Script can read the real transaction
   fields by reading the (now-pinned) witness bytes. See [`techniques.md`](techniques.md) §1.
2. **Preimage decomposition** — emulate the disabled `OP_SUBSTR` with `OP_CAT` + `OP_SIZE` +
   witness padding, extracting and checking any field of the 212-byte tapscript signature-message
   preimage. See [`techniques.md`](techniques.md) §2.

Together they recover `sha_outputs` (demo 1), `sha_prevouts` (demo 2), and extend to
`sha_amounts`, `sha_sequences`, etc.

## Files

| File | What it is |
|------|------------|
| [`Capability_Parity_CSFS_CAT_Covenants.pdf`](Capability_Parity_CSFS_CAT_Covenants.pdf) | The full paper (byte-level constructions, every TXID inline, capability coverage table). |
| [`output_binding.md`](output_binding.md) | Demo 1 byte-for-byte: tapscript ASM, witness layout, hardcoded values, why a boundary-shift fails. |
| [`input_binding.md`](input_binding.md) | Demo 2: same technique on `sha_prevouts`; the BitVM co-spend connector. |
| [`techniques.md`](techniques.md) | Same-signature binding (§3.2) and preimage decomposition (§3.3), in plain language. |
| [`../eltoo/`](../eltoo/) | Demo 3 — the runnable CSFS+CTV eltoo ladder (`csfs_ladder_ctv.py`), already in this repo. |

## Companion Delving Bitcoin threads (full witness traces)

- Output binding (demo 1): https://delvingbitcoin.org/t/taproot-native-prevout-binding-via-sighash-preimage-decomposition/2483/3
- Input binding (demo 2): https://delvingbitcoin.org/t/taproot-native-prevout-binding-via-sighash-preimage-decomposition/2483
- Eltoo ladder (demo 3): https://delvingbitcoin.org/t/eltoo-state-chain-on-signet-again-three-rounds-two-transactions-csfs-ctv-with-rekey-and-ladder-no-cat/2430

## Honest boundaries

- **Capability, not efficiency.** These constructions are larger in script and witness than the
  dedicated opcodes; that is exactly what a specialized opcode buys.
- **Signer-participating spends only.** Same-signature binding needs a spending signature, so
  keyless covenants are out of scope.
- **Eltoo is CSFS+*CTV*, O(n).** Demo 3 reaches APO's eltoo *topology* via an O(n) delegation
  ladder with CTV settlement — not APO's constant-size rebinding primitive, and not via CAT.

## Reproduce

Demo 3 is runnable from this repo (`examples/eltoo/`, see its README). Demos 1–2 are verifiable
directly from their confirmed witnesses: open the TXIDs above on a signet explorer and check the
revealed tapscript and witness against [`output_binding.md`](output_binding.md) /
[`input_binding.md`](input_binding.md). All spends are on Bitcoin Inquisition signet, where
BIP-347 (CAT) and BIP-348 (CSFS) are activated.
