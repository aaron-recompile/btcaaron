# Draft Email: Request for Testing (btcaaron + btcrun)

Subject: Request for testing: btcaaron + btcrun Core-testing preview (Taproot experiment workflows)

Hi all,

I am sharing a public testing preview of `btcaaron + btcrun`, focused on reducing startup cost for Bitcoin Core-oriented Taproot testing workflows.

This is **not** a replacement for Core's functional test framework, and not a production wallet release.  
The goal is to provide a lightweight contributor ramp for reproducible experiments and failure analysis.

## What is included

- Taproot transaction construction workflows (key-path and script-path)
- Mutation-based negative testing (control block, signature, output mutations)
- Policy vs consensus split experiments
- Cross-instance consistency runner (e.g., regtest + testnet3)
- Standardized outputs for easier review (`CASE/EXPECT/ACTUAL/VERDICT`)

## What has been validated so far

- Task 2: control-block mutation matrix (`5/5 PASS`)
- Task 3: signature/output correctness matrix (`4/4 PASS`)
- Task 4: policy-vs-consensus split matrix (`4/4 PASS`)
- Task 7: cross-instance consistency (`3/3 CONSISTENT` on regtest/testnet3)

## What I would like feedback on

1. Are the rejection categories and interpretations clear/useful?
2. Are there additional high-value Taproot edge cases we should include?
3. Is the cross-instance comparison output actionable enough for regression work?
4. Any concerns about workflow design before broader testing outreach?

## Quick start (from repo root)

```bash
python3 examples/core_test/scenarios/task2_controlblock_mutation_matrix.py regtest
python3 examples/core_test/scenarios/task3_sig_output_correctness_matrix.py regtest
python3 examples/core_test/scenarios/task4_policy_consensus_split_matrix.py regtest
python3 examples/core_test/scenarios/task7_cross_instance_consistency_runner.py testnet3 regtest
```

Documentation index:

- `examples/core_test/INDEX.md`

Please share issues, suggestions, or result logs via GitHub issues.

Thanks for your time and testing help.

Best,  
Aaron Zhang

