# Task 2 Result Note: Control-Block Mutation Matrix

## What this task validates

Task 2 validates a transaction-level loop for Taproot script-path testing:

1. Construct a valid script-path spend with `btcaaron`.
2. Inject targeted witness/control-block mutations.
3. Run `testmempoolaccept` and classify reject reasons.
4. Confirm baseline transaction can be mined (consensus anchor).

This is the intended closed loop:

`construct -> inject failure -> localize error`.

## Environment and scope

- Chain: `regtest`
- Runner: `btcrun regtest rpc ...`
- Script: `examples/core_test/task2_controlblock_mutation_matrix.py`
- Network mode: `BTCAARON_NETWORK: regtest`
- Wallet dependency: none (receiver address generated locally)

## Cases and outcomes

From the latest run:

- `controlblock/baseline_valid_scriptpath` -> `PASS`
  - `allowed=true`
- `controlblock/flip_last_byte` -> `PASS`
  - `allowed=false`
  - reject category: `WITNESS_PROGRAM_MISMATCH`
- `controlblock/truncate_one` -> `PASS`
  - `allowed=false`
  - reject category: `CONTROL_BLOCK_SIZE`
- `controlblock/append_zero` -> `PASS`
  - `allowed=false`
  - reject category: `CONTROL_BLOCK_SIZE`
- `controlblock/consensus_baseline_mined` -> `PASS`
  - `confirmations=1`

Summary: `5/5 PASS`.

## Why this matters for btcaaron

This experiment demonstrates concrete strengths of `btcaaron` as a protocol test scaffold:

- **Fast valid baseline construction**
  - Taproot script-path tx is built through a compact high-level flow.
- **Failure injection at byte level**
  - Raw witness mutation can be layered on top without changing btcaaron core APIs.
- **Deterministic error localization**
  - Failures separate into distinct classes (size vs hash mismatch), not just generic rejection.
- **Policy + consensus linkage**
  - Same setup supports mempool rejection analysis and successful block inclusion checks.
- **Teaching and research readiness**
  - Output contract (`CASE/EXPECT/ACTUAL/VERDICT`) is reproducible and easy to review.

## Positioning statement (for reports/proposals)

Task 2 shows that `btcaaron` is not only a transaction builder but a lightweight Taproot experiment harness.  
It supports reproducible negative testing with meaningful error classification while preserving a valid baseline path that can be mined.

## What is still not covered

Task 2 is focused on control-block mutation only. It does not yet cover:

- broader policy-vs-consensus split cases (Task 4),
- cross-instance consistency runs (Task 7),
- signature/output invariant matrix expansion (Task 3).

## Reproduce

From repository root:

```bash
python3 examples/core_test/scenarios/task2_controlblock_mutation_matrix.py regtest
```

