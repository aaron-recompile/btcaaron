# btcaaron ⇄ python-bitcoin-utils equivalence (verification record)

Date: 2026-06-23. Verifier: venv `experiment/venv` (Python 3.11), btcaaron 0.2.3.

## What was checked
The paper's experiments were **actually built with python-bitcoin-utils**
(`four_leaf_lib.py`, `two_leaf_lib.py`) — that is the code path that produced the
on-chain testnet3/signet/mainnet TXIDs. `four_leaf_btcaaron.py` re-expresses the
identical experiment through btcaaron's declarative `TapTree` / `SpendBuilder` API.
We verified btcaaron reproduces it faithfully.

## Results

**Address (definitive):** with the same two signet keys, both libraries produce the
*identical* on-chain signet four-leaf address
`tb1pf5rhd89h6hpgcf9eah2xxp4wnn9qzadlp56yj2vck8uu86erre4qg9vcse`.
⇒ tree shape (balanced depth-2 `[[hash,2of2],[csv,sig]]`), all four leaf templates,
and internal-key handling are byte-for-byte identical.

**Leaf templates (identical):**
- hash: `OP_SHA256 <sha256("helloworld")> OP_EQUALVERIFY OP_TRUE`
- 2of2: `OP_0 <alice> OP_CHECKSIGADD <bob> OP_CHECKSIGADD OP_2 OP_EQUAL`
- csv : `<seq=2> OP_CHECKSEQUENCEVERIFY OP_DROP <bob> OP_CHECKSIG`
- sig : `<bob> OP_CHECKSIG`

**Spends (same keys, same UTXO, testnet):**
| path | check | result |
|---|---|---|
| hashlock | full-tx byte-identical (deterministic, no signature) | ✅ identical |
| keypath  | witness structure (1 sig) | ✅ identical |
| multisig | witness [sig,sig,script,cb] — script+control-block | ✅ identical |
| csv      | witness [sig,script,cb] — script+control-block + nSequence | ✅ identical |
| sig      | witness [sig,script,cb] — script+control-block | ✅ identical |

Signature paths differ only in the Schnorr signature bytes (random aux/nonce) —
expected; the deterministic hashlock spend is byte-identical end to end.

## btcaaron limitations found (candidates to fix upstream)
1. **regtest collapses to testnet.** `Key.from_wif` normalizes by WIF prefix; regtest
   and testnet share `0xef`, so a regtest WIF is treated as testnet and addresses come
   out `tb1…` not `bcrt1…`. ⇒ btcaaron can't address/spend on regtest from a WIF.
   (The bitcoin-utils reference handles regtest fine via `setup("regtest")`.)
2. **`Transaction.hex` / `.txid` are `@property`**, not methods — call without `()`.

## Files
- reference (proven, on-chain): `four_leaf_lib.py`
- btcaaron declarative edition:  `four_leaf_btcaaron.py`
- regtest rehearsal (btcaaron):  `rehearse_btcaaron_regtest.py` (blocked only by limitation #1)
- equivalence comparators:       `/tmp/cmp_btcaaron.py`, `/tmp/cmp_spend.py` (ad-hoc)
