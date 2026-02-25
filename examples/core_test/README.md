# core_test

Core-facing integration experiment workspace for `btcaaron + btcrun`.

This folder is for reproducible Taproot testing workflows (policy/consensus behavior, failure injection, and cross-instance checks), not just offline transaction construction demos.

## Structure

- `framework/`
  - `outer_experiment_framework.py` (Task 5/6 base layer)
- `scenarios/`
  - runnable task scripts (Task 1/2/3/4/7 and demos)
- `results/`
  - result notes, comparisons, value scoreboard
- `research/`
  - feasibility and productization analysis docs
- `enablement/`
  - rollout, checklist, and pilot feedback templates
- `sources/`
  - external-source buckets (`core_pr`, `stackexchange`, `inquisition`, `gsr`)

## Prerequisites

- `btcaaron` installed from this repo (recommended: editable install)
- [`btcrun`](https://github.com/aaron-recompile/btcrun) available in your environment
- running Bitcoin node instances for integration scenarios:
  - required: `regtest`
  - optional but recommended: `testnet3` (for cross-instance comparisons)

Quick start for nodes:

```bash
btcrun start regtest
btcrun start testnet3
btcrun status
```

## Run

From repo root:

```bash
python3 examples/core_test/scenarios/demo_34076_outer_framework.py testnet3
python3 examples/core_test/scenarios/tutorial_triplet.py testnet3
python3 examples/core_test/scenarios/tutorial_tx_policy_consensus.py regtest
python3 examples/core_test/scenarios/task2_controlblock_mutation_matrix.py regtest
python3 examples/core_test/scenarios/task3_sig_output_correctness_matrix.py regtest
python3 examples/core_test/scenarios/task4_policy_consensus_split_matrix.py regtest
python3 examples/core_test/scenarios/task7_cross_instance_consistency_runner.py testnet3 regtest
```

## Modes

- **Library mode (btcaaron only)**  
  Build/sign/serialize flows without requiring a local node.

- **Integration mode (btcaaron + btcrun + bitcoind)**  
  Required for `core_test` scenarios that call RPC (`testmempoolaccept`, mining, cross-instance checks).

## Notes

- The framework remains outside btcaaron core APIs (phase-1 boundary).
- Requires btcaaron deps (or at least `bitcoin-utils`) in runtime environment.
