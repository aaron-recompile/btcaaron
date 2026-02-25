# Contributor Training & Productization Playbook

## Why this note exists

This note captures the practical thesis behind `btcrun + btcaaron`:

- not replacing Bitcoin Core tests,
- but productizing the contributor ramp into a reproducible training pipeline.

---

## 1) Before vs now: how tester training changes

## Before (traditional path)

New contributors typically needed to:

1. understand Core test framework architecture first,
2. navigate large functional test files and helpers,
3. add/modify edge cases inside existing harness patterns,
4. interpret failures mixed with framework-level complexity.

Common bottlenecks:

- high startup cost,
- high cognitive overhead before first useful result,
- slow iteration on small negative-test ideas.

## Now (btcrun + btcaaron ramp)

Contributors can start from focused scripts that provide:

1. compact tx/descriptor construction,
2. explicit mutation points,
3. standardized output (`CASE/EXPECT/ACTUAL/VERDICT`),
4. easy RPC execution against known instances.

Result:

- earlier "first success",
- clearer mapping from mutation -> rejection category,
- faster conversion from learner to experiment contributor.

---

## 2) What we trained with (task-by-task)

## Task 1 (tutorial triplet)

- **Learner goal**: understand valid/invalid/nonstandard-candidate framing.
- **What is tested**: descriptor parser behavior and failure expectation.
- **Skill trained**: forming hypotheses and reading parser errors.

## Transaction tutorial (key-path baseline)

- **Learner goal**: see valid spend, invalid signature, and mined baseline.
- **What is tested**: policy acceptance + consensus confirmation.
- **Skill trained**: separating "mempool outcome" from "chain outcome".

## Task 2 (control-block mutation matrix)

- **Learner goal**: witness-level mutation literacy.
- **What is tested**: control block structure/content failure classes.
- **Skill trained**: byte-level fault injection and reject classification.

## Task 3 (signature + output correctness matrix)

- **Learner goal**: internalize signature commitment semantics.
- **What is tested**: signature tamper and output tamper both breaking validation.
- **Skill trained**: reasoning about digest commitments, not just signature bytes.

## Task 4 (policy vs consensus split)

- **Learner goal**: stop conflating policy reject with consensus invalid.
- **What is tested**: high-fee policy rejection vs relaxed-policy mining.
- **Skill trained**: interpreting local policy guards correctly.

## Task 7 (cross-instance consistency)

- **Learner goal**: trust results only when reproducible across instances.
- **What is tested**: outcome class consistency across `testnet3` and `regtest`.
- **Skill trained**: behavioral comparison and divergence diagnosis.

## Task 8 / 8.1 (teaching + pilot feedback loop)

- **Learner goal**: move from personal run to cohort-scale reproducibility.
- **What is tested**: training delivery quality and iteration readiness.
- **Skill trained**: report writing, interpretation quality, and experiment design proposals.

---

## 3) Suggested training path (time + ability)

| Stage | Tasks | Estimated time | Entry ability | Exit ability |
|---|---|---:|---|---|
| Foundation | Task 1 + Tx tutorial | 1.0-1.5 h | basic Python + terminal | can run and interpret baseline vs invalid |
| Mutation literacy | Task 2 + Task 3 | 1.5-2.0 h | understands witness basics | can design and classify negative cases |
| Validation layers | Task 4 | 0.75-1.0 h | knows mempool/block basics | can explain policy vs consensus split |
| Reproducibility | Task 7 | 0.5-0.75 h | can run scripts on two instances | can identify consistency/divergence signals |
| Cohort output | Task 8 report | 0.5-1.0 h | above completed | can produce reviewable evidence note |

**Total typical ramp**: ~4.25 to 6.25 hours for a first complete cycle.

---

## 4) What our toolchain decouples

`btcaaron + btcrun` decouples contributor ramp-up from immediate deep framework dependence:

1. **Experiment logic** vs **framework internals**
   - learners focus on mutation/result semantics first.
2. **Case authoring** vs **harness plumbing**
   - adding a case is closer to "declare + mutate + classify."
3. **Diagnosis** vs **log archaeology**
   - standardized case output reduces interpretation noise.
4. **Training delivery** vs **ad hoc mentoring**
   - handouts/rubrics/scripts make instruction repeatable.

This is why it is "front-loaded productization": it packages the early contributor journey.

---

## 5) Why this matters (project-level significance)

1. Lowers first-contribution friction for Bitcoin testing learners.
2. Increases throughput of test-literate contributors in cohort settings.
3. Produces structured, auditable evidence useful for grants and engineering planning.
4. Creates a reusable bridge from educational labs to Core-oriented testing tasks.

---

## 6) What we can extend next

## Near-term extensions

1. **Policy matrix expansion**
   - broader policy toggles (relay limits, standardness dimensions).
2. **Sighash family matrix**
   - compare multiple sighash contexts under controlled output/input mutations.
3. **Script-path depth matrix**
   - multiple leaf depths and merkle path mutation classes.
4. **Cross-version comparison**
   - run Task 7 against different node builds for regression signals.

## Mid-term extensions

1. **Automated result aggregation**
   - batch run + markdown/json summary generation.
2. **Teaching analytics**
   - correlate learner errors with task difficulty for curriculum tuning.
3. **Issue/PR-ready export**
   - one-click transformation from lab output to issue evidence format.

## Long-term potential

1. "Contributor readiness benchmark" suite.
2. Shared public mutation corpus for protocol testing education.
3. Integration path from ramp scripts -> selected Core test contributions.

---

## 7) Recommended next execution order (from here)

1. Run first Task 8 pilot with 5-15 learners.
2. Collect Task 8.1 feedback artifacts.
3. Score improvements via prioritization rubric.
4. Build one new matrix extension (high-score candidate).
5. Re-run pilot and compare learning signal quality.

This closes a real product loop: **build -> teach -> measure -> improve**.

