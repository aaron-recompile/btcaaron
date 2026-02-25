# Task 8: 15-Minute Teaching Script

## Minute 0-2: Frame

"Today we are not replacing Bitcoin Core tests. We are building contributor ramp-up muscle: reproduce, mutate, classify, explain."

## Minute 2-5: Task 2 hook

- Show one valid script-path case.
- Show one control-block mutation failure.
- Ask: "What changed? Bytes or policy?"  
Expected learner answer: witness/control-block structure or commitment mismatch.

## Minute 5-8: Task 3 hook

- Show output mutation case and `INVALID_SCHNORR_SIGNATURE`.
- Ask: "Why signature failure if signature bytes unchanged?"  
Expected learner answer: tx digest commitment includes outputs.

## Minute 8-11: Task 4 hook

- Show strict/default rejection for high-fee tx.
- Show relaxed-policy mined outcome for same tx.
- Emphasize: `policy reject != consensus invalid`.

## Minute 11-13: Task 7 hook

- Show same target case classification across `testnet3` and `regtest`.
- Emphasize reproducibility as confidence amplifier.

## Minute 13-15: Assignment brief

Deliverable:

- one report with command evidence and interpretation,
- one proposed mutation case with expected reject category.

Evaluation:

- correctness of interpretation > volume of logs.

