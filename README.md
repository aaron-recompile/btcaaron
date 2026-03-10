# btcaaron<img src="images/mark.png" width="52" alt="btcaaron mark" style="margin-left:4px;vertical-align:middle" />

[![Supported by OpenSats](https://img.shields.io/badge/supported%20by-OpenSats-orange?style=flat-square&logo=bitcoin)](https://opensats.org)

A pragmatic Bitcoin toolkit with a clear path toward full Taproot engineering.

Designed for reproducible testnet experiments, educational workflows, and script-path development.

If you find btcaaron useful, a GitHub star is appreciated.

## Current Status

**v0.2.1 (alpha preview)** — Core Taproot spend-path workflows are implemented and testnet/regtest-verified.  
Current focus is release hardening: broader validation coverage, documentation alignment, and contributor testing feedback.

## Features

### Available Now (v0.1.x)

Production-tested on testnet with real transactions:

- Generate Legacy / SegWit / Taproot addresses from WIF
- UTXO scanning and balance lookup via public APIs
- Build and sign standard transactions
- Broadcast to Blockstream / Mempool endpoints
- Developer helpers (`WIFKey`, `quick_transfer`)

### Available Now (v0.2.1 - Alpha Preview)

Testnet-verified with real transactions (23 tests, all passing):

- Declarative Taproot tree builder (`.hashlock()`, `.multisig()`, `.timelock()`, `.checksig()`)
- Script-path and key-path spend constructors
- Automatic witness construction and signature ordering
- All 5 spend paths verified: hashlock, multisig, checksig, CSV timelock, keypath
- Real transaction TXID reproduction tests

### Future (v0.3.x+)

- PSBT v2 hardening and broader interoperability validation
- Custom script templates
- Multi-input/output transactions

## Positioning (Quick Comparison)

> High-level developer-experience comparison only (not a full feature matrix).

| Library | Typical Use Case | Script-Path UX |
|---|---|---|
| `python-bitcoin-utils` | Low-level transaction/script construction and protocol experiments | Manual (build tree/witness/control-block flow yourself) |
| `btcaaron` | Fast Taproot prototyping, teaching workflows, and reproducible test scaffolds | Declarative (e.g., `.hashlock()`, `.multisig()`, `.timelock()`) |
| `BitcoinLib` | Wallet-oriented workflows, account management, and persistence layers | Mostly automated for common wallet flows |
| `embit` | Descriptor/PSBT flows and hardware-wallet-oriented integrations | Descriptor-oriented, standard-policy paths |

_Optional note_: `btcaaron` is designed as a pragmatic Taproot engineering layer on top of low-level primitives, prioritizing readability and reproducible testing workflows.

## Requirements

- Python `>=3.10,<3.13`
- Dependencies:
  - `requests>=2.25.0,<3.0.0`
  - `bitcoin-utils>=0.7.3,<0.8.0`

## Installation

```bash
python -m pip install btcaaron
```

Or from source:

```bash
git clone https://github.com/aaron-recompile/btcaaron.git
cd btcaaron
python -m pip install -e .
```

### IDE environment tip (important)

Most IDE terminals run `python`/`python3` from the currently selected interpreter.
Install and run with the same interpreter to avoid mismatched environments:

```bash
python -m pip install -e .
btcaaron-doctor
```

## Quick Start

```python
from btcaaron import WIFKey, quick_transfer

wif = "your_testnet_wif"

key = WIFKey(wif)
print("Taproot:", key.get_taproot().address)

balance = key.get_taproot().get_balance()
print("Balance:", balance, "sats")

if balance > 1000:
    txid = quick_transfer(wif, "taproot", "tb1q...", amount=500, fee=300)
    print("Broadcasted:", txid)
```

## v0.2.1 API Example

*Taproot-native API — core features available now.*

```python
from btcaaron import Key, TapTree

alice = Key.from_wif("cRxebG...")
bob = Key.from_wif("cSNdLF...")

program = (TapTree(internal_key=alice)
    .hashlock("secret", label="hash")
    .multisig(2, [alice, bob], label="2of2")
    .timelock(blocks=144, then=bob, label="csv")
    .checksig(bob, label="backup")
).build()

print(program.address)  # tb1p...

# Fund commit address without leaving IDE (auto UTXO selection)
from btcaaron import fund_program
# txid = fund_program(wif, program, 10_000)  # 打币到 program.address

tx = (program.spend("hash")
    .from_utxo("abc123...", 0, sats=1200)
    .to("tb1p...", 666)
    .unlock(preimage="secret")
    .build())

tx.broadcast()
```

Full specification in [DESIGN.md](./DESIGN.md).

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

Run specific test suites:

```bash
# v0.2.1 comprehensive tests (pytest)
python -m pytest tests/test_btcaaron_v02.py -v

# v0.1.x example-based tests
python tests/test_btcaaron_v01.py
```

## Environment Doctor

Use doctor before reporting install/runtime issues:

```bash
btcaaron-doctor
```

If doctor fails, re-install with the same interpreter:

```bash
python -m pip install -e .
btcaaron-doctor
```

## Project Structure

```
btcaaron/
├── btcaaron/         # Core library
├── tests/            # Test suite
├── DESIGN.md         # Architecture & roadmap
├── README.md
├── setup.py
└── LICENSE
```

## Development

See [DESIGN.md](./DESIGN.md) for architecture details and development roadmap.

## Notes

- **Default safety posture**: testnet/regtest-first for everyday development and experiments.
- **Mainnet (experimental)**: available behind explicit guardrails in `Transaction.broadcast(...)`.
- **Mainnet guardrails**:
  - default call blocks mainnet broadcast unless `allow_mainnet=True`
  - `dry_run=True` is available for no-side-effect routing checks
  - recommended smoke script: `python3 examples/core_test/scenarios/mainnet_readiness_smoke.py`
- **v0.2.1 Status**: Core Taproot spend-path flows are implemented and testnet-verified; ongoing work focuses on hardening, PSBT, and documentation.

## Acknowledgments

Development of btcaaron is supported by an [OpenSats](https://opensats.org) grant.  
OpenSats supports open-source contributors working on Bitcoin and related freedom tech.

## Author

**Aaron Zhang**  
Reproducible Taproot experiments · Script engineering · Educational tooling  
https://x.com/aaron_recompile

## License

MIT License