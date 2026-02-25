# Task 8 Instructor Guide

## Session objective

Move learners from "can run script" to "can reason about validation layers":

- signature validity,
- witness/control-block structure,
- policy filters vs consensus validity,
- cross-instance reproducibility.

## Suggested flow (60 minutes)

1. **10 min**: context and terminology
2. **15 min**: Task 2 run + discussion
3. **10 min**: Task 3 run + digest commitment concept
4. **10 min**: Task 4 policy/consensus split
5. **10 min**: Task 7 consistency and bug-confidence framing
6. **5 min**: assignment briefing

## Expected learner conclusions

- Task 2: different control-block mutations fail for different reasons.
- Task 3: outputs are signed commitments, not independent post-sign edits.
- Task 4: mempool policy and consensus are related but distinct layers.
- Task 7: reproducibility across instances strengthens trust in findings.

## Common confusion points

- "Rejected by mempool" means invalid forever.
  - Correction: policy reject can still be consensus-valid.
- "Only signature bytes matter for signature validity."
  - Correction: signature commits to tx digest (including outputs under default sighash context).
- "Same failure text must match exactly across versions."
  - Correction: classify semantically, not by one rigid phrase.

## TA checks during live lab

- Ensure students use `regtest` for Tasks 2/3/4.
- Ensure students report at least one reject category per mutation task.
- Ensure students do not treat `RPC_OFFLINE` as behavioral divergence in Task 7.

