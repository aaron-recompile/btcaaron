# Changelog

All notable changes to btcaaron. Versions follow the releases published on PyPI.

## Unreleased (on `main`)

- BIP 446 `OP_TEMPLATEHASH` template hash (`btcaaron.templatehash`), cross-checked against Bitcoin Inquisition v29.4; TEMPLATEHASH + CSFS + IK eltoo example.
- BIP 341 signature-message preimage module (`compute_sigmsg_preimage`, `compute_sigmsg_digest`).
- External (non-program) inputs in `SpendBuilder`.
- Tapscript v2 leaf version constant (`LEAF_VERSION_TAPSCRIPT_V2`).
- BIP 118 ANYPREVOUT signature message (`bip118_sighash`, `Key.sign_taproot_script_bip118`, `TapTree.bip118_checksig`) and per-input script-path signing.
- Inquisition templates for `OP_INTERNALKEY` (`inq_internalkey_*`).
- Reproduction packages in `examples/`: eltoo (CSFS ladder + CTV), Braidpool, Taproot engineering paper, CSFS+CAT covenant parity.
- API reference (`docs/API.md`), CONTRIBUTING guide, CI, MIT `LICENSE` file.

## 0.2.3 — 2026-03-22

- Bitcoin Inquisition script templates: `OP_CAT`, `OP_CHECKSIGFROMSTACK`, `OP_CHECKTEMPLATEVERIFY` (`inq_*`), and node RPC helpers.
- `INQUISITION.md`; README and PyPI metadata refresh; `__version__` consistency test.

## 0.2.2 — 2026-03-10

- Mainnet-readiness guardrails and the `btcaaron-doctor` environment check.
- Regtest bech32/bech32m address prefixes in `SpendBuilder`.
- PSBT v0 with multi-UTXO support; PSBT `tap_merkle_root` (BIP 371); `PsbtV2` (BIP 370).
- `quick_transfer` Taproot auto-UTXO selection, `fund_program`, dust-limit checks, clearer broadcast errors.
- `TapTree` supports arbitrary leaf counts; duplicate leaf labels rejected (contributed by @beihaili).

## 0.2.1 — 2026-02-12

- Packaging release following 0.2.0.

## 0.2.0 — 2026-02-12

- Taproot-native API: `Key`, declarative `TapTree` (`hashlock`, `multisig`, `timelock`, `checksig`, `custom`), `TaprootProgram`, `SpendBuilder`.
- `RawScript` and `tapmath` for arbitrary tapscript including Inquisition opcodes.
- All five spend paths (hashlock, multisig, checksig, CSV timelock, key path) verified against confirmed testnet transactions; TXID reproduction tests.

## 0.1.1 — 2025-08-09

- Initial release: Legacy / SegWit / Taproot addresses from WIF, UTXO lookup, build/sign/broadcast standard transactions (`WIFKey`, `quick_transfer`).
