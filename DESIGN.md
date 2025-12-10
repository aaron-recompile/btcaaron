# btcaaron Architecture Design

> **Version**: 1.0.0-draft  
> **Status**: In Development  
> **Last Updated**: 2025-12

## Vision

btcaaron is a **Taproot-native** Bitcoin development toolkit designed to make Taproot script-path engineering as intuitive as writing natural language.

Most Bitcoin libraries treat Taproot as an afterthought—bolted onto Legacy and SegWit foundations. btcaaron flips this: **Taproot is the first-class citizen**.

## Design Goals

| Goal | Description |
|------|-------------|
| **Semantic API** | Write intent (`.hashlock()`), not opcodes (`OP_SHA256`) |
| **Progressive Complexity** | One line to send, ten lines for 4-leaf trees, full control when needed |
| **Explainability** | Every operation can `.explain()` itself—perfect for learning |
| **Clean Boundaries** | Building, spending, and broadcasting are separate concerns |

## Core API Preview

### Building a 4-Leaf Taproot Tree

```python
from btcaaron import Key, TapTree

alice = Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob = Key.from_wif("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")

program = (TapTree(internal_key=alice)
    .hashlock("helloworld", label="hash")       # SHA256 hash lock
    .multisig(2, [alice, bob], label="2of2")    # 2-of-2 with CHECKSIGADD
    .timelock(blocks=2, then=bob, label="csv")  # CSV relative timelock
    .checksig(bob, label="bob")                 # Simple signature
).build()

print(program.address)     # tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q
print(program.leaves)      # ["hash", "2of2", "csv", "bob"]
program.visualize()        # ASCII tree diagram
```

### Spending via Script Path

```python
# Hash lock path - provide preimage
tx = (program.spend("hash")
    .from_utxo("245563c5aa4c...", 0, sats=1200)
    .to("tb1p060z97...", 666)
    .unlock(preimage="helloworld")
    .build())

# Multisig path - signatures auto-ordered internally  
tx = (program.spend("2of2")
    .from_utxo("1ed5a3e97a6d...", 0, sats=1400)
    .to("tb1p060z97...", 668)
    .sign(alice, bob)
    .build())

# CSV timelock - nSequence auto-configured
tx = (program.spend("csv")
    .from_utxo("9a2bff416141...", 0, sats=1600)
    .to("tb1p060z97...", 800)
    .sign(bob)
    .build())
```

### Spending via Key Path (Maximum Privacy)

```python
tx = (program.keypath()
    .from_utxo("42a9796a91cf...", 0, sats=2000)
    .to("tb1p060z97...", 888)
    .sign(alice)
    .build())

tx.broadcast()
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Code                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Key ────► TapTree ────► TaprootProgram ────► SpendBuilder     │
│  (keys)    (builder)      (frozen tree)       (tx builder)      │
│               │                │                   │            │
│               │ .build()       │ .spend()          │ .build()   │
│               ▼                ▼                   ▼            │
│        LeafDescriptor    ControlBlock        Transaction        │
│                                                   │             │
│                                                   │ .broadcast()│
│                                                   ▼             │
│                                               Provider          │
│                                            (network layer)      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    bitcoin-utils (dependency)                   │
└─────────────────────────────────────────────────────────────────┘
```

## Type Responsibilities

| Type | Responsibility | Mutability |
|------|----------------|------------|
| `Key` | Key management, signing, pubkey export | Immutable |
| `TapTree` | Collect leaf scripts, organize tree structure | Mutable (builder) |
| `TaprootProgram` | Address, Merkle root, ControlBlock generation | Immutable |
| `SpendBuilder` | UTXO selection, witness assembly, signing | Mutable (builder) |
| `Transaction` | Serialization, broadcast, explanation | Immutable |

## Key Design Decisions

### 1. Label-First Leaf Access

Leaves are accessed by semantic labels, not fragile indices:

```python
program.spend("hash")    # ✅ Recommended - stable across refactors
program.spend(0)         # ⚠️  Allowed but discouraged
```

### 2. Builder / Program Separation

`TapTree` (mutable builder) and `TaprootProgram` (immutable result) are distinct types. This enforces clean boundaries and prevents accidental tree modification after commitment.

### 3. Smart Unlock Handling

`SpendBuilder` reads `LeafDescriptor.script_type` and `params` to automatically handle:

- **HASHLOCK**: SHA256 verification of preimage
- **MULTISIG**: Signature ordering per CHECKSIGADD semantics  
- **CSV_TIMELOCK**: nSequence configuration
- **KEYPATH**: Tweaked key signing

### 4. Extensibility via Custom Scripts

Built-in methods cover common patterns. Escape hatches exist for advanced users:

```python
# Full control when needed
program = (TapTree(alice)
    .hashlock("secret", label="hash")           # Built-in
    .custom(my_script, label="experimental")    # Custom script
).build()

# Manual witness for custom scripts
tx = (program.spend("experimental")
    .from_utxo(...)
    .to(...)
    .unlock_with([element1, element2, element3])
    .build())
```

## Module Structure

```
btcaaron/
├── __init__.py              # Exports: Key, TapTree, Script, Transaction
├── key.py                   # Key class
├── tree/
│   ├── builder.py           # TapTree (builder pattern)
│   ├── program.py           # TaprootProgram (immutable)
│   └── leaf.py              # LeafDescriptor
├── spend/
│   ├── builder.py           # SpendBuilder
│   └── transaction.py       # Transaction
├── script/
│   ├── script.py            # Script class
│   └── templates.py         # HTLC, Vault, etc. (future)
├── explain/
│   ├── program.py           # ProgramExplanation
│   └── transaction.py       # TransactionExplanation
├── network/
│   ├── provider.py          # Provider base class
│   ├── mempool.py           # Mempool.space adapter
│   └── blockstream.py       # Blockstream.info adapter
└── _internal/
    └── bitcoinutils.py      # bitcoin-utils wrapper
```

## Roadmap

### Phase 1: Core Foundation (Month 1-2)
- [x] Architecture design
- [ ] `Key` class implementation
- [ ] `TapTree` builder with semantic leaf methods
- [ ] `TaprootProgram` with address generation
- [ ] Milestone: Generate correct 4-leaf Taproot address

### Phase 2: Spending Paths (Month 2-3)
- [ ] `SpendBuilder` core structure
- [ ] Script path spending (hashlock, checksig, multisig, timelock)
- [ ] Key path spending
- [ ] Milestone: Reproduce all Chapter 8 transactions

### Phase 3: Network & PSBT (Month 3-4)
- [ ] Provider implementations (Mempool, Blockstream)
- [ ] Multi-provider broadcast with failover
- [ ] PSBT v2 support (Taproot-aware)

### Phase 4: Visualization & Education (Month 4-5)
- [ ] `.explain()` for Program and Transaction
- [ ] ASCII/Mermaid tree visualization
- [ ] Script execution simulator

### Phase 5: Polish & Release (Month 5-6)
- [ ] Comprehensive test suite
- [ ] Documentation and tutorials
- [ ] Community testing
- [ ] v1.0.0 release

## Validation Criteria

The following on-chain transactions must be reproducible with exact TXID match:

| Spend Path | Expected TXID |
|------------|---------------|
| Hashlock | `1ba4835fca1c94e7eb0016ce37c6de2545d07d84a97436f8db999f33a6fd6845` |
| Multisig | `1951a3be0f05df377b1789223f6da66ed39c781aaf39ace0bf98c3beb7e604a1` |
| CSV Timelock | `98361ab2c19aa0063f7572cfd0f66cb890b403d2dd12029426613b40d17f41ee` |
| Simple Sig | `1af46d4c71e121783c3c7195f4b45025a1f38b73fc8898d2546fc33b4c6c71b9` |
| Key Path | `1e518aa540bc770df549ec9836d89783ca19fc79b84e7407a882cbe9e95600da` |

## Contributing

This design document serves as the north star for development. API changes require updating this document first.

For detailed technical specifications, see `docs/ARCHITECTURE.md`.

## License

MIT License