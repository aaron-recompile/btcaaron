# Task 8 Teaching Pack (Chaincode Cohort)

## Goal

Convert completed experiments into a cohort-ready training pack so learners can:

1. run reproducible Taproot experiments,
2. interpret policy/consensus outcomes,
3. map results to contributor-level testing intuition.

## Audience

- Primary: Chaincode learners new to Bitcoin Core testing
- Secondary: mentors evaluating contributor readiness

## Learning objectives

By the end of the pack, learners should be able to:

- explain `policy reject != consensus invalid`,
- reproduce controlled Taproot failures (signature/control block),
- classify rejection categories from RPC output,
- compare outcomes across two instances (`regtest`, `testnet3`),
- summarize findings in `CASE/EXPECT/ACTUAL/VERDICT` format.

## Pack contents

- `task8_lab_student_handout.md`
  - learner-facing lab instructions
- `task8_lab_instructor_guide.md`
  - TA/instructor walkthrough and expected interpretation
- `task8_grading_checklist.md`
  - objective pass criteria for quick review
- `task8_15min_teaching_script.md`
  - short lecture/demo script for cohort kickoff

## Required scripts (already in repo)

- `tutorial_tx_policy_consensus.py`
- `task2_controlblock_mutation_matrix.py`
- `task3_sig_output_correctness_matrix.py`
- `task4_policy_consensus_split_matrix.py`
- `task7_cross_instance_consistency_runner.py`

## Outcome artifact expected from each learner

One markdown report containing:

1. command list executed,
2. key result excerpts,
3. one paragraph per task (2/3/4/7) with interpretation,
4. one proposed new mutation case.

