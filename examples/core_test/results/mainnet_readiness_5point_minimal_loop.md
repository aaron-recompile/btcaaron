# Mainnet Readiness: 5-Point Minimal Loop

This is a safety-first readiness loop for `btcaaron` mainnet paths without
broadcasting transactions.

## Scope

- Objective: verify mainnet-capable code paths are wired and guarded
- Non-goal: real mainnet broadcast in this step

## 5 checks

1. **Network propagation**
   - `Key.generate(network="mainnet")` now sets bitcoinutils context.
   - `TapTree(..., network="mainnet")` persists normalized network in `TaprootProgram`.
2. **Address correctness**
   - Mainnet Taproot program should derive `bc1p...` addresses.
3. **Broadcast routing introspection**
   - `Transaction.broadcast_plan()` exposes side-effect-free routing info.
4. **No-side-effect rehearsal**
   - `Transaction.broadcast(dry_run=True)` prints route/txid plan and never pushes.
5. **Mainnet safety guard**
   - `Transaction.broadcast(...)` blocks mainnet by default.
   - Explicit opt-in required: `allow_mainnet=True`.

## Smoke script

```bash
python3 examples/core_test/scenarios/mainnet_readiness_smoke.py
```

Expected outcome:

- `ALL 5 CHECKS PASSED`
- no transaction is broadcast

## Notes

- If dependencies are missing, install runtime requirements first:
  - `bitcoin-utils`
  - `requests`
- For release messaging, keep "mainnet experimental" wording until
  external-mainnet evidence is collected.
