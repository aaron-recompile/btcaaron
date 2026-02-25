# feature_taproot.py Rewrite Feasibility (btcaaron + btcrun)

Date: 2026-02-21  
Scope: research analysis (no btcaaron implementation changes)

## 1) File Overview

- Target file: `bitcoin/test/functional/feature_taproot.py`
- Reference companion: `bitcoin/test/functional/wallet_taproot.py` (comparison only)
- Total lines:
  - `feature_taproot.py`: 1899
  - `wallet_taproot.py`: 505
- Core architecture in `feature_taproot.py`:
  - Context signing framework (`DEFAULT_CONTEXT`, `get`, `override`, `getter`) enables composable spend mutations.
  - `make_spender()` wraps scriptPubKey construction + valid/invalid spend lambda generation.
  - `add_spender()` registers test cases into a large randomized execution pool.
  - `test_spenders()` generates funding UTXOs, builds randomized multi-input txs, precomputes success/failure witnesses, tests mempool policy + block consensus.
  - `run_test()` executes:
    1) deterministic vector scenario (`gen_test_vectors`)
    2) post-activation consensus pool (`sample_spenders + spenders_taproot_active`)
    3) nonstandard pool (`spenders_taproot_nonstandard`) in isolation and mixed mode.

### Spender runtime scale (measured)

Runtime-generated spender counts:

- `spenders_taproot_active()`: 2793
- `spenders_taproot_nonstandard()`: 4
- `sample_spenders()`: 3

Total unique spender definitions used by `run_test`: 2800.

Prefix distribution (`spenders_taproot_active`):

- `unkver` 756, `opsuccess` 696, `sighash` 569, `applic` 256, `alwaysvalid` 169, `legacy` 128, `tapscript` 79, `sighashcache` 50, `siglen` 40, `compat` 32, `spendpath` 10, `sig` 5, `output` 2, `case24765` 1.

## 2) Architecture Notes

### make_spender / Spender tuple

`Spender = (script, comment, is_standard, sat_function, err_msg, sigops_weight, no_fail, need_vin_vout_mismatch)`

- `script`: funded scriptPubKey for the test UTXO
- `comment`: test id/category marker (also used in reporting)
- `is_standard`: policy expectation for valid variant
- `sat_function(tx, idx, utxos, valid)`: returns `(scriptSig, witness_stack)` for either valid or forced-invalid variant
- `err_msg`: expected block-reject substring for failing variant
- `sigops_weight`: pre-taproot sigops accounting contribution
- `no_fail`: whether this test has no invalid branch
- `need_vin_vout_mismatch`: enables targeted `SIGHASH_SINGLE` input/output index mismatch coverage

### Context signing framework

- Design pattern: dataflow graph over lazily evaluated expressions.
- `sat_function` exists because each test can generate both a valid spend and a controlled invalid spend by overriding only selected context keys (`failure` dict).
- This avoids duplicating tx assembly logic while maximizing mutation coverage.

### add_spender registration + batch execution

- `add_spender` appends generated `Spender` objects into category pools.
- `test_spenders` randomizes grouping, input count mix, locktime/version/sequence, and valid/invalid toggles.
- For each transaction, each input is failed once (if possible) plus one all-valid pass.

### run_test flow

- `gen_test_vectors`: deterministic BIP341/342-style vector scenario.
- `consensus_spenders`: broad consensus validation campaign.
- `nonstd_spenders`: policy-valid but nonstandard cases, tested both isolated and mixed.

## 3) Scenario Classification Table

Notes:
- "Line range" is where category registration logic lives.
- "Scenario count" is runtime-generated spenders (not just static `add_spender` call count).
- "Core LOC" / "btcaaron estimate" are conservative implementation LOC for that category's harness logic.

| Category | Line range | Scenario count | Core LOC | btcaaron estimate | Reduction | Priority | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| BIP340 sig mutation (`sig`) | 684-699 | 5 | 16 | 10-14 | 10-35% | 4 | Straightforward sign/bitflip checks |
| Invalid internal key (`output`) | 700-737 | 2 | 38 | 20-28 | 25-47% | 4 | Needs invalid-x handling parity |
| Taproot sighash matrix (`sighash`) | 738-805 | 569 | 105 | 70-95 | 10-33% | 3 | Annex/codesep/hashtype byte mutation gaps |
| Signature length edge cases (`siglen`) | 807-842 | 40 | 36 | 28-40 | -10%-22% | 3 | Byte-precise mutation heavy |
| Applicability by witver/witlen/p2sh (`applic`) | 843-864 | 256 | 22 | 22-40 | -80%-0% | 2 | Core loops already compact |
| Spending path integrity (`spendpath`) | 865-916 | 10 | 53 | 30-40 | 25-43% | 4 | Good fit for control-block mutation helpers |
| Tapscript edge rules (`tapscript`) | 918-1140 | 79 | 223 | 160-210 | 6-28% | 2 | Many consensus-specific stack/opcode limits |
| Unknown leaf version (`unkver`) | 1142-1167 | 756 | 26 | 30-60 | -130% to -15% | 2 | Runtime-large but source-loop tiny |
| OP_SUCCESS family (`opsuccess`) | 1168-1211 | 696 | 44 | 50-90 | -105% to -14% | 1 | Similar: many runtime cases from short loops |
| Nonsuccess opcode guard (`alwaysvalid`) | 1200-1211 | 169 | 12 | 12-20 | -66%-0% | 2 | Small isolated check |
| Issue #24765 regression (`case24765`) | 1212-1217 | 1 | 6 | 8-12 | -100% to -33% | 2 | Valuable, but tiny |
| Legacy mix-in (`legacy`) | 1218-1229 | 128 | 12 | 30-70 | -483% to -150% | 1 | btcaaron focus is taproot, not legacy policy matrix |
| Compatibility guard (`compat`) | 1231-1237 | 32 | 7 | 15-30 | -329% to -114% | 1 | Core-side low-level script engine check |
| Sighash caching stress (`sighashcache`) | 1238-1302 | 50 | 65 | 45-65 | 0-31% | 3 | Possible with loops; needs careful opcode/CS checks |
| Nonstandard-but-valid (`inactive`) | 1305-1322 | 4 | 20 | 12-18 | 10-40% | 4 | Good btcrun policy/consensus split example |
| Tutorial sample (`tutorial`) | 1326-1359 | 3 | 34 | 12-18 | 47-65% | 5 | Best "showcase" rewrite target |

## 4) Dependencies and Portability

### Core test_framework dependencies (feature_taproot)

Heavy usage of:

- `blocktools` (`create_block`, `create_coinbase`, witness commitment)
- `messages` (`CTransaction`, `CTxIn`, `CTxOut`, serialization control)
- `script` internals (`TaprootSignatureMsg`, BIP341 hash fragments, opcode constants)
- `key` internals (`generate_privkey`, `compute_xonly_pubkey`, `sign_schnorr`, tweak functions)
- `wallet`/RPC utilities + assertion helpers

### test_framework-specific features (no direct btcaaron equivalent)

- Fine-grained block assembly and sigops budget engineering in Python test harness.
- Deterministic tx-level vector dumps wired to Core consensus flags and fuzz infra format.
- Unified random campaign driver that mixes:
  - policy admission checks
  - block acceptance checks
  - per-input fail toggles in same tx skeleton.

### btcaaron / python-bitcoinutils capabilities already present

- Taproot key-path and script-path signing (`sign_taproot_input` used in btcaaron).
- Taproot tree construction, control block generation, merkle root handling.
- Custom script leaf support (`RawScript`, custom witness path).
- PSBT v0/v2 flows (taproot fields present in btcaaron PSBT classes).
- `btcrun` orchestration for multi-chain instance/RPC command routing.

## 5) wallet_taproot.py vs feature_taproot.py (why this matters)

- `wallet_taproot.py` is primarily wallet descriptor behavior:
  - descriptor import/derivation
  - sendtoaddress behavior
  - PSBT wallet process/finalize flow
- `feature_taproot.py` is consensus/policy stress harness:
  - malformed witness/sighash/script edge conditions
  - block-level acceptance logic
  - large randomized spender campaigns

Conclusion: `wallet_taproot.py` is easier for high-level btcaaron parity demos; `feature_taproot.py` is harder but better for protocol-test scaffolding credibility.

## 6) Recommended First Rewrite Batch (3-5 categories)

### A) `tutorial` (Priority 5)

- Why first: highest clarity and best LOC reduction.
- Rewrite shape:
  - `TapTree.custom(...)` + `SpendBuilder` + btcrun `getdescriptorinfo` / `testmempoolaccept`.
  - Keep one valid + one controlled-invalid branch.

### B) `spendpath` control-block integrity (Priority 4)

- Why: strong Taproot-core narrative (merkle depth, negflag, control block length/bitflip).
- Rewrite shape:
  - Use `TaprootProgram.control_block()` then mutate bytes intentionally.
  - Submit via btcrun to policy + mined block checks.

### C) `sig` + `output` (Priority 4)

- Why: compact but high-value BIP340/BIP341 sanity checks.
- Rewrite shape:
  - baseline valid keypath spend + injected key/sighash/signature perturbations.
  - dedicated invalid-internal-key test for witness mismatch behavior.

### D) `inactive` nonstandard cases (Priority 4)

- Why: shows btcrun value (same spend, different acceptance contexts).
- Rewrite shape:
  - explicit standardness vs consensus acceptance split script.

### E) `sighashcache` (Priority 3, optional in batch-1)

- Why: demonstrates loop-based compression potential.
- Caveat: still low-level; include only if time permits.

## 7) btcaaron Gap List (for this rewrite program)

- Annex-aware signing/witness mutation helpers  
  - Gap: no first-class annex knob in current high-level builder.  
  - Difficulty: medium (touch sign/witness API design).

- Codeseparator-position and leaf-version override control in sighash context  
  - Gap: Core harness exposes these as first-class context overrides; btcaaron does not.  
  - Difficulty: medium-high.

- Unified "valid vs invalid" twin-generation abstraction (Core-style `failure` overlay)  
  - Gap: currently manual per scenario.  
  - Difficulty: medium.

- Block-construction utility layer comparable to Core `blocktools`  
  - Gap: btcrun gives RPC orchestration, but not Python block assembly helpers.  
  - Difficulty: medium.

- Legacy/witv0 mixed-matrix and pre-taproot compatibility campaign  
  - Gap: possible at low level but out-of-scope for taproot-focused lightweight harness.  
  - Difficulty: high / low ROI.

- P2P relay-level policy behavior  
  - Gap: not a btcaaron target (RPC-driven harness).  
  - Difficulty: unrealistic for this stack.

## 8) Methodology Revision (Important)

The initial framing leaned too much on "line-for-line replacement".  
Revised evaluation lens:

1. **Standalone runnability** (outside Core internal test framework)
2. **Startup cost** (time from zero to first successful run)
3. **Cognitive cost** (how much framework internals a new contributor must understand)
4. **Teaching readability** (script usefulness as educational material)

So, avoid centering the narrative on "34%-47% coverage".  
For grants/community messaging, "high-value scenario completion + startup-cost drop" is stronger.

### Startup Cost Comparison (recommended external narrative)

- Core path: compile Core (~30 min) -> learn test_framework (~2h) -> run target test
- btcaaron path: install deps (~1 min) -> read script (~10 min) -> run target test

## 9) Candidate Work Items and Execution Order (Revised)

Execution order:

**5 -> 6 -> 1 -> 8 -> 2 -> 3 -> 4 -> 7 -> 9**

Why:
- Front-load infra (5/6), then every scenario rewrite gets cheaper and more consistent.
- Move teaching packaging (8) right after first concrete scenario (1), so cohort feedback drives priorities.

### Phase-1 boundary

- Build an **outer experimental framework** under `examples/core_test/`
- Do **not** modify btcaaron core APIs yet
- Re-evaluate core API changes only after 2-3 scenarios prove stable reuse

### Work items (in revised order)

1. **Lightweight failure-injection abstraction (feature opportunity)**  
   - Core-inspired overlay model in btcaaron style

2. **Reproducible output contract**  
   - Standard `CASE / EXPECT / ACTUAL / VERDICT` format

3. **Rewrite `tutorial` triplet**  
   - valid / invalid / nonstandard, with docs and expected outcomes

4. **Teaching pack for Chaincode cohort**  
   - 5-10 minute notes per scenario

5. **`spendpath` control-block mutation matrix**  
   - negflag flip, merkle bitflip, trunc/pad control block

6. **`sig` + `output` correctness baseline**  
   - signature/sighash mutation + invalid internal key

7. **`inactive` policy-vs-consensus split**  
   - same tx in mempool-policy and block-consensus contexts

8. **Cross-instance consistency runner**  
   - regtest/testnet3/mainnet matrix via btcrun

9. **Small `sighashcache` PoC (optional)**  
   - representative subset first, not full matrix

One-line positioning (revised):

> btcaaron + btcrun is valuable not because it "replaces Core lines", but because it turns high-value Taproot protocol tests into standalone, teachable, reproducible engineering assets.

