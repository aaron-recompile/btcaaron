# btcaaron <img src="images/mark.png" width="48" alt="btcaaron mark" />

A pragmatic Bitcoin toolkit with a clear path toward full Taproot engineering.

Designed for reproducible testnet experiments, educational workflows, and script-path development.

## Current Status

**v0.1.1** — Stable foundation release.  
Core utilities actively used in my Taproot engineering work and on-chain experiments.

**v0.2.0** — Core Taproot spend-path prototype implemented and testnet-verified.  
All 5 spend paths working with real transactions. Next: hardening, PSBT support, and comprehensive documentation. See [DESIGN.md](./DESIGN.md) for roadmap.

## Features

### Available Now (v0.1.x)

Production-tested on testnet with real transactions:

- Generate Legacy / SegWit / Taproot addresses from WIF
- UTXO scanning and balance lookup via public APIs
- Build and sign standard transactions
- Broadcast to Blockstream / Mempool endpoints
- Developer helpers (`WIFKey`, `quick_transfer`)

### Available Now (v0.2.0 - Prototype)

Testnet-verified with real transactions (23 tests, all passing):

- Declarative Taproot tree builder (`.hashlock()`, `.multisig()`, `.timelock()`, `.checksig()`)
- Script-path and key-path spend constructors
- Automatic witness construction and signature ordering
- All 5 spend paths verified: hashlock, multisig, checksig, CSV timelock, keypath
- Real transaction TXID reproduction tests

### Future (v0.3.x+)

- PSBT v2 support (Taproot-aware)
- Custom script templates
- Multi-input/output transactions

## Requirements

- Python >= 3.7
- Dependencies: `requests>=2.25.0`, `bitcoin-utils>=0.7.1`

## Installation

```bash
pip install btcaaron
```

Or from source:

```bash
git clone https://github.com/aaron-recompile/btcaaron.git
cd btcaaron
pip install .
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

## v0.2.0 API Example

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
# v0.2.0 comprehensive tests (pytest)
python -m pytest tests/test_btcaaron_v0.2.py -v

# v0.1.x example-based tests
python tests/test_btcaaron_v0.1.py
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

- **Testnet Only**: This toolkit is designed for testnet use. Mainnet support may be added in future versions.
- **v0.2.0 Status**: Core Taproot spend-path flows are implemented and testnet-verified; ongoing work focuses on hardening, PSBT, and documentation.

## Author

**Aaron Zhang**  
Reproducible Taproot experiments · Script engineering · Educational tooling  
https://x.com/aaron_recompile

## License

MIT License