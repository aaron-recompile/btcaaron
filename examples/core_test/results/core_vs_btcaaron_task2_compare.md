# Core vs btcaaron (Task 2): Control-Block Mutation Matrix

## Purpose

This note compares how a Taproot control-block mutation experiment is approached in:

- Bitcoin Core functional-test ecosystem (sipa-style framework usage)
- `btcaaron + btcrun` lightweight experiment workflow

Scope is intentionally narrow: **Task 2 only** (script-path baseline + control-block mutations + error localization).

## Methodology note (important)

This is **not** a claim that `btcaaron` replaces Bitcoin Core tests.  
Bitcoin Core functional tests optimize for full-node correctness and long-term regression coverage.  
This comparison focuses on a different objective: **startup cost and experiment iteration speed** for research/teaching scenarios.

## Task 2 outcome evidence

- Script: `examples/core_test/scenarios/task2_controlblock_mutation_matrix.py`
- Latest run summary: `5/5 PASS`
- Cases covered:
  - baseline valid script-path spend (policy pass)
  - control-block byte flip (hash mismatch class)
  - control-block truncate (size class)
  - control-block append (size class)
  - baseline mined (consensus anchor)

## Side-by-side comparison

| Dimension | Core functional-test style | btcaaron Task 2 style | Why it matters |
|---|---|---|---|
| Primary goal | Full-node regression assurance | Focused protocol experiment | Different optimization target |
| Setup surface | Core test framework, harness conventions, spender/context patterns | One script + `btcrun regtest` | Lower startup friction |
| Baseline tx construction | Embedded in larger framework flow | Fluent API (`TapTree` + `spend().build()`) | Faster to author/modify |
| Failure injection | Via framework context/signing patterns | Direct witness-level mutation on raw tx | Easier to target single fault |
| Error observation | Framework assertions + logs | Structured output (`CASE/EXPECT/ACTUAL/VERDICT`) + reject categories | Better teaching/debug readability |
| Error localization | Often requires navigating framework layers | Immediate class labels (`CONTROL_BLOCK_SIZE`, `WITNESS_PROGRAM_MISMATCH`) | Faster root-cause triage |
| Policy/consensus linkage | Powerful, but tied to framework orchestration | Same script checks mempool + mined confirmation | Compact end-to-end loop |
| Reusability for cohort labs | Higher onboarding overhead | Copy-run-modify workflow | Better classroom fit |

## What btcaaron clearly saves in Task 2

1. **Startup cost**  
   The experiment can be reproduced from a single script and a local regtest instance.

2. **Cognitive overhead for first contribution**  
   Contributors can focus on Taproot behavior (control block semantics), not framework internals first.

3. **Iteration latency for new negative cases**  
   Adding a new mutation is a small local edit (mutator function + case row).

4. **Communication cost**  
   Output contract is immediately presentation-ready for issue notes, grant updates, and teaching handouts.

## Where Core remains stronger

- Broad consensus and policy regression breadth
- P2P and node-behavior integration coverage
- Long-horizon maintenance confidence across releases

`btcaaron` complements this by accelerating focused experiments, not by replacing Core's regression role.

## Grant-facing positioning (short)

Task 2 demonstrates that `btcaaron` enables a reproducible Taproot failure-injection loop with explicit error localization while keeping a valid mined baseline path.  
Compared with full-framework workflows, it reduces startup and explanation cost for protocol research and teaching use cases.

## Reproduce

```bash
python3 examples/core_test/scenarios/task2_controlblock_mutation_matrix.py regtest
```

