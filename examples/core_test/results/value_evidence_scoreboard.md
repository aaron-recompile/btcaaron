# btcaaron + btcrun Value Evidence Scoreboard (Phase 1)

This page tracks concrete experiment evidence for the value claim:

> lower startup cost for Bitcoin protocol testing, while keeping reproducible and meaningful failure diagnostics.

## Completed experiments

| Task | Script | Focus | Latest result | Key evidence |
|---|---|---|---|---|
| Task 1 | `tutorial_triplet.py` | descriptor-level tutorial triplet | `3/3 PASS` | valid/invalid/nonstandard-candidate flow works under unified output contract |
| Tx tutorial | `tutorial_tx_policy_consensus.py` | key-path policy + consensus | `3/3 PASS` | valid passes and mines; wrong-key rejects with Invalid Schnorr signature |
| Task 2 | `task2_controlblock_mutation_matrix.py` | script-path control-block mutation | `5/5 PASS` | reject classes separate into `WITNESS_PROGRAM_MISMATCH` and `CONTROL_BLOCK_SIZE` |
| Task 3 | `task3_sig_output_correctness_matrix.py` | signature and output integrity | `4/4 PASS` | signature tamper and output tamper both trigger `INVALID_SCHNORR_SIGNATURE` |
| Task 4 | `task4_policy_consensus_split_matrix.py` | policy vs consensus split | `4/4 PASS` | high-fee tx is policy-rejected by default/strict profile but mined when local maxfeerate guard is relaxed |
| Task 7 | `task7_cross_instance_consistency_runner.py` | cross-instance consistency | `3/3 CONSISTENT` | control cases are stable and nested `pk(musig(...))` failure class is consistent on `testnet3` and `regtest` |
| Task 8 | `task8_teaching_pack_overview.md` (+4 docs) | cohort teaching pack | `DELIVERED` | student handout, instructor guide, grading checklist, and 15-min script are ready for pilot |
| Task 8.1 | `task8_1_*` templates | pilot feedback loop | `DELIVERED` | student form, instructor retro, and prioritization rubric enable iteration after first cohort run |

## What value is now empirically demonstrated

1. **Constructive path is real**  
   btcaaron-built Taproot txs pass policy and can be mined on regtest.

2. **Failure injection is practical**  
   Mutations can be applied at witness/serialized-tx layer without core API redesign.

3. **Error localization is useful**  
   Failures map into interpretable categories instead of generic failure-only signals.

4. **Output format is reusable**  
   `CASE/EXPECT/ACTUAL/VERDICT` supports issue notes, grant updates, and cohort assignments.

## Remaining high-value gaps

- Task 8 pilot execution and first feedback cycle analysis

