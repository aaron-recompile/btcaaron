# Contributing to btcaaron

Thanks for your interest. btcaaron is a small, research-oriented toolkit; contributions that make Taproot and covenant experiments easier to build and to reproduce are very welcome.

## Reporting bugs and asking questions

- Open an issue at <https://github.com/aaron-recompile/btcaaron/issues>.
- For a bug, include the btcaaron version (`python -c "import btcaaron; print(btcaaron.__version__)"`), Python version, network (testnet, signet, regtest, Inquisition signet), a minimal script, and the full error. Never paste private keys or WIFs that hold real funds.
- Questions about usage are fine as issues too; label them `question`.

## Development setup

```bash
git clone https://github.com/aaron-recompile/btcaaron.git
cd btcaaron
python -m pip install -e . pytest
python -m pytest -q
```

Supported Python versions are 3.10–3.12. Five interactive tests that broadcast real transactions are skipped by default. A few legacy v0.1 tests (UTXO scan, balance check) query public testnet block explorers; the v0.2 tests and the reference-vector tests run offline.

## Pull requests

1. Fork the repository and create a branch from `main`.
2. Add or update tests for any behaviour change; `python -m pytest -q` must pass (CI runs it on 3.10–3.12).
3. Keep the public API documented: new public functions and classes need a docstring. Regenerate the API reference with `python tools/gen_api.py` (writes `docs/API.md`).
4. For anything consensus- or signature-related (sighash, control blocks, Inquisition opcodes), include a test vector from the relevant BIP or a confirmed transaction you have reproduced.
5. Describe what you changed and why in the pull request.

## Scope

In scope: Taproot construction and spending, signature-message tooling, PSBT, and templates for opcodes active on Bitcoin Inquisition signet. Mainnet use is possible but the project is alpha software; experimental Inquisition features must stay clearly separated from default behaviour.

## Support and governance

btcaaron is maintained by Aaron Zhang (@aaron-recompile). Issues and pull requests are usually answered within a week. Design decisions are discussed in issues; the maintainer makes the final call and records larger decisions in `DESIGN.md`.

## Code of conduct

Be respectful and constructive. Harassment or personal attacks are not tolerated; the maintainer may close or lock threads that violate this.
