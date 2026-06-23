# On-chain verification of all paper TXIDs (local full nodes)

Date 2026-06-23. Verified against local **mainnet** node (height 955074) and the
**inquisition signet** node (height 310137) via btcrun. This is the check the
other reviewer could not run (no block-explorer access in its sandbox).

## Mainnet (§6.4 capstone — the contested core claim)
| ID | TXID | Block | Witness check |
|----|------|-------|---------------|
| M1 | 9fc1923c…dc363 | 954955 | 1 item (bot key/sig spend) — the front-run replacement |
| M2 | 4986e0ad…966c1 | 954956 | **3 items, item[0] = `68656c6c6f776f726c64` = "helloworld"** ✓ |
| M3 | 16c1b282…44a0f2 | 954956 | 1 item (bot spend) |

**M2 is the smoking gun:** its witness literally begins with the bytes of
`helloworld`, then the hashlock script + control block — exactly as §6.4 states
("whose witness is exactly helloworld + our hashlock script + the leaf-0 control
block"). Byte-level confirmed on mainnet.

**Author's replaced spend `44bb8526…`:** correctly **ABSENT** from mainnet — it was
RBF-evicted by M1. This *validates* the "replaced by" claim rather than weakening it;
it is a mempool-only transaction with no confirmed txid (so it cannot appear in
Appendix A as a confirmed entry — see review note).

## Signet (§6.2–6.3 clean demonstrations)
All seven found on the inquisition signet node by block scan:
S1 9d3d6d3b…7643 · S2 7d7d064c…ce508 · S3 35d14e2f…abf4b · S4 c1b7f11a…73604 ·
S6 a5e38453…73d8c8 · S7 643a8f2b…d977ba → **block 310043**;  S5 a69cd325…4fc48a → **block 310045**.

## Result
**10/10 TXIDs confirmed on-chain.** The paper's central empirical claim
(public-preimage hashlock front-running + weak-leaf reuse) is verified at the
witness-byte level, not just by format.
