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

- Bitcoin Core (`bitcoind`) installed and in PATH
- `btcaaron` installed from this repo: `pip install -e .`
- `bitcoin-utils` installed: `pip install bitcoin-utils`
- [`btcrun`](https://github.com/aaron-recompile/btcrun) installed and configured (`~/.btcrun/config.toml`)
- A running `regtest` instance (optional: `testnet3` for cross-instance comparisons)

> **Tip:** use `python3 -m pip install` to ensure packages go into the same Python you run scripts with.

## Quickstart (regtest)

```bash
# 1. install deps
pip install -e .              # btcaaron
pip install bitcoin-utils

# 2. install and configure btcrun (see btcrun README)
#    make sure ~/.btcrun/config.toml has a valid datadir for regtest

# 3. start node
btcrun start regtest
btcrun status                 # should show: regtest ✓ connected

# 4. run tutorial (from btcaaron repo root)
python3 examples/core_test/scenarios/tutorial_tx_policy_consensus.py regtest
# expected: SUMMARY: 3/3 PASS
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

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'bitcoinutils'` | `pip install bitcoin-utils` |
| `Read-only file system: '/path'` | Edit `~/.btcrun/config.toml`, set `datadir` to a real path |
| Deps installed but import still fails | `which python3` — may point to a different Python than where deps are installed |

## Notes

- The framework remains outside btcaaron core APIs (phase-1 boundary).
- Requires btcaaron deps (or at least `bitcoin-utils`) in runtime environment.
