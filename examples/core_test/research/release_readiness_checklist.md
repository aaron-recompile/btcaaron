# Release Readiness Checklist (Core-Testing Preview)

Use this checklist before posting to the Bitcoin Core dev list.

## Scope Declaration

- [ ] Release scope is explicitly "public testing preview", not production/mainnet wallet tooling.
- [ ] README and announcement language are aligned with this scope.
- [ ] Mainnet claims are conservative and explicit about current limits.

## Repository Hygiene

- [ ] `git status` clean (no accidental temp/cache files).
- [ ] No `__pycache__` or local artifacts included.
- [ ] File paths in docs match current folder structure.

## Version and Metadata Consistency

- [ ] `setup.py` version matches intended release tag.
- [ ] README "Current Status" matches actual implementation state.
- [ ] Test command examples in README are valid.
- [ ] Project maturity label (alpha/beta wording) matches reality.

## Core Experiment Smoke Tests

- [ ] `tutorial_triplet.py` runs and produces expected summary.
- [ ] `tutorial_tx_policy_consensus.py` runs on regtest.
- [ ] `task2_controlblock_mutation_matrix.py` passes expected matrix.
- [ ] `task3_sig_output_correctness_matrix.py` passes expected matrix.
- [ ] `task4_policy_consensus_split_matrix.py` demonstrates policy/consensus split.
- [ ] `task7_cross_instance_consistency_runner.py` reports consistency or actionable divergence.

## Evidence Artifacts

- [ ] Latest outputs are captured in result notes.
- [ ] `value_evidence_scoreboard.md` is up to date.
- [ ] One short "what to test" list is prepared for external testers.

## Safety / Mainnet Guardrails

- [ ] Any mainnet-capable paths are documented with warnings.
- [ ] Default recommended commands are testnet/regtest-first.
- [ ] No announcement language implies fund-safety guarantees.

## Community Feedback Path

- [ ] Issue template or guidance for bug reports prepared.
- [ ] Contact path included (repo issue + optional email/handle).
- [ ] Requested tester focus areas are clearly listed.

## Go / No-Go

- [ ] GO: all critical boxes above checked.
- [ ] NO-GO: blockers listed with owner + ETA below.

### Blockers (if any)

1.
2.
3.

