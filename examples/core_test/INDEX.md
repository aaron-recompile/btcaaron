# core_test INDEX

Minimal navigation for the Core-facing experiment workspace.

## 1) Start here

- Overview: `examples/core_test/README.md`
- Framework base: `examples/core_test/framework/outer_experiment_framework.py`

## 2) Run order (recommended)

From repository root:

```bash
python3 examples/core_test/scenarios/tutorial_triplet.py testnet3
python3 examples/core_test/scenarios/tutorial_tx_policy_consensus.py regtest
python3 examples/core_test/scenarios/task2_controlblock_mutation_matrix.py regtest
python3 examples/core_test/scenarios/task3_sig_output_correctness_matrix.py regtest
python3 examples/core_test/scenarios/task4_policy_consensus_split_matrix.py regtest
python3 examples/core_test/scenarios/task7_cross_instance_consistency_runner.py testnet3 regtest
```

## 3) Read results

- Task 2 note: `examples/core_test/results/task2_result_note.md`
- Task 3 note: `examples/core_test/results/task3_result_note.md`
- Task 4 note: `examples/core_test/results/task4_result_note.md`
- Task 7 note: `examples/core_test/results/task7_result_note.md`
- Evidence scoreboard: `examples/core_test/results/value_evidence_scoreboard.md`
- Core comparison (Task 2): `examples/core_test/results/core_vs_btcaaron_task2_compare.md`

## 4) External-source buckets

- Core PR: `examples/core_test/sources/core_pr/`
- StackExchange: `examples/core_test/sources/stackexchange/`
- Inquisition: `examples/core_test/sources/inquisition/`
- GSR: `examples/core_test/sources/gsr/`

