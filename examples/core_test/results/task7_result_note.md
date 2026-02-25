# Task 7 Result Note: Cross-Instance Consistency Runner

## What this task validates

Task 7 validates that the same descriptor matrix produces stable outcomes across multiple node instances.

This checks whether experiment conclusions are portable across environments, not just locally accidental.

## Environment and scope

- Script: `examples/core_test/task7_cross_instance_consistency_runner.py`
- Instances in latest run: `testnet3`, `regtest`
- Method: run identical `getdescriptorinfo` cases and compare per-case outcome classes

## Latest observed outcomes

- `control/musig_keypath`
  - `testnet3`: `OK`
  - `regtest`: `OK`
  - verdict: `CONSISTENT`

- `control/plain_pk_timelock`
  - `testnet3`: `OK`
  - `regtest`: `OK`
  - verdict: `CONSISTENT`

- `target/nested_pk_musig`
  - `testnet3`: `ERR_INVALID_MUSIG`
  - `regtest`: `ERR_INVALID_MUSIG`
  - verdict: `CONSISTENT`

Summary: `3/3 cases CONSISTENT (excluding offline instances)`.

## Interpretation

1. Control cases agree across instances, so baseline parser behavior is stable.
2. The target nested `pk(musig(...))` failure is reproduced on both instances.
3. The bug signal is instance-consistent, increasing confidence that this is not an environment-specific artifact.

## Why this matters for btcaaron + btcrun

- **Cross-instance portability**: same experiment harness works across different btcrun targets.
- **Regression monitoring ready**: when a node upgrades/fixes behavior, this runner will surface divergence immediately.
- **Contributor workflow value**: learners can reproduce and compare outcomes without entering Core's full test framework first.

## Note on output fix

The runner output logic was updated so `ACTUAL` correctly reflects `success` vs `error` for each instance row.

## Reproduce

```bash
python3 examples/core_test/scenarios/task7_cross_instance_consistency_runner.py testnet3 regtest
```

