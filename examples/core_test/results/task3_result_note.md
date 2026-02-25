# Task 3 Result Note: Signature + Output Correctness Matrix

## What this task validates

Task 3 validates Taproot key-path signature integrity on two mutation axes:

1. Signature bytes are tampered.
2. Output amount is tampered after signing.

Both cases should fail because Schnorr verification is bound to transaction digest commitments.

## Environment and scope

- Chain: `regtest`
- Runner: `btcrun regtest rpc ...`
- Script: `examples/core_test/task3_sig_output_correctness_matrix.py`
- Network mode: `BTCAARON_NETWORK: regtest`
- Wallet dependency: none

## Cases and outcomes

From the latest run:

- `sig_output/baseline_valid_keypath` -> `PASS`
  - `allowed=true`
- `sig_output/mutate_signature_flip_last_byte` -> `PASS`
  - `allowed=false`
  - reject category: `INVALID_SCHNORR_SIGNATURE`
- `sig_output/mutate_output_amount_minus_one` -> `PASS`
  - `allowed=false`
  - reject category: `INVALID_SCHNORR_SIGNATURE`
- `sig_output/consensus_baseline_mined` -> `PASS`
  - `confirmations=1`

Summary: `4/4 PASS`.

## Why this matters for btcaaron

This experiment shows that `btcaaron` can serve as a correctness-focused Taproot lab:

- **Baseline reliability**: valid key-path tx reaches mempool and gets mined.
- **Negative testing support**: byte-level mutation can be layered on serialized tx.
- **Digest integrity demonstration**: output mutation invalidates signature as expected.
- **Fast teaching narrative**: one script demonstrates both "valid path" and "why it fails".

## Positioning statement (for reports/proposals)

Task 3 demonstrates that `btcaaron + btcrun` can verify Taproot signing invariants with reproducible, mutation-driven checks.  
It helps newcomers test and understand signature commitments without entering the full Core test harness first.

## Reproduce

```bash
python3 examples/core_test/scenarios/task3_sig_output_correctness_matrix.py regtest
```

