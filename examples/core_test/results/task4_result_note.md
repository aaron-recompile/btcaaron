# Task 4 Result Note: Policy vs Consensus Split Matrix

## What this task validates

Task 4 validates a practical policy-vs-consensus split:

1. A normal-fee Taproot tx passes mempool policy.
2. A high-fee Taproot tx is rejected under stricter/default local policy.
3. The same high-fee tx remains consensus-valid and can be mined once the local policy guard is relaxed.

This demonstrates a key testing concept:

`policy reject != consensus invalid`.

## Environment and scope

- Chain: `regtest`
- Runner: `btcrun regtest rpc ...`
- Script: `examples/core_test/task4_policy_consensus_split_matrix.py`
- Network mode: `BTCAARON_NETWORK: regtest`
- Wallet dependency: none

## Observed run (`4/4 PASS`)

Observed outcomes:

- `policy_consensus/baseline_normal_fee_policy` -> `PASS`
- `policy_consensus/high_fee_strict_policy_reject` -> `PASS`
- `policy_consensus/high_fee_default_send_reject` -> `PASS`
- `policy_consensus/high_fee_relaxed_policy_mined` -> `PASS`

Summary: `4/4 PASS`.

Note on robustness:

- Some nodes report `max-fee-exceeded`.
- Others report `Fee exceeds maximum configured by user ...`.
- The matcher now accepts both forms to keep result classification stable.

## Why this matters for btcaaron + btcrun

Task 4 shows the framework can teach and verify policy boundaries in a compact workflow:

- **Build once, test multiple policy profiles** with the same transaction.
- **Diagnose local policy guards** without confusing them with consensus failure.
- **Show controllable transition** from reject to mined by changing policy input (`maxfeerate` argument).
- **Preserve reproducible reporting** under `CASE/EXPECT/ACTUAL/VERDICT`.

## Positioning statement (for reports/proposals)

Task 4 demonstrates that `btcaaron + btcrun` can make policy-vs-consensus distinctions concrete and reproducible for contributors.  
It reduces onboarding confusion around mempool rejection semantics while retaining consensus-grounded validation.

## Reproduce

```bash
python3 examples/core_test/scenarios/task4_policy_consensus_split_matrix.py regtest
```

