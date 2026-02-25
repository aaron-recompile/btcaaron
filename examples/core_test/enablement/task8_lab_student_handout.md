# Task 8 Student Lab Handout

## Setup

Run from repository root:

```bash
python3 examples/core_test/scenarios/tutorial_tx_policy_consensus.py regtest
python3 examples/core_test/scenarios/task2_controlblock_mutation_matrix.py regtest
python3 examples/core_test/scenarios/task3_sig_output_correctness_matrix.py regtest
python3 examples/core_test/scenarios/task4_policy_consensus_split_matrix.py regtest
python3 examples/core_test/scenarios/task7_cross_instance_consistency_runner.py testnet3 regtest
```

## What to capture

For each script, capture:

- final `SUMMARY` line,
- one representative `CASE` block,
- one sentence interpretation.

## Questions to answer

1. In Task 2, what is the difference between `CONTROL_BLOCK_SIZE` and `WITNESS_PROGRAM_MISMATCH`?
2. In Task 3, why can output mutation trigger `INVALID_SCHNORR_SIGNATURE` without touching signature bytes?
3. In Task 4, why can the same tx be rejected first and mined later?
4. In Task 7, what does cross-instance consistency tell you about bug confidence?
5. Propose one additional mutation case you want to test next.

## Submission template

Create `my_task8_report.md` with sections:

- `## Commands Run`
- `## Task 2`
- `## Task 3`
- `## Task 4`
- `## Task 7`
- `## Proposed Next Mutation`

Each task section must include:

- one command,
- one output excerpt,
- one interpretation paragraph (3-5 lines).

