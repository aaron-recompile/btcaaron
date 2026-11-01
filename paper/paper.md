---
title: 'btcaaron: a Python toolkit for reproducible Taproot script-path and covenant experiments on Bitcoin'
tags:
  - Python
  - Bitcoin
  - Taproot
  - cryptocurrency
  - reproducibility
authors:
  - name: Aaron Zhang
    orcid: 0009-0001-1599-092X
    affiliation: 1
affiliations:
  - name: Independent developer, United States
    index: 1
date: 1 November 2026
bibliography: paper.bib
---

# Summary

Bitcoin coins are locked by small programs called scripts. Since the Taproot upgrade
of 2021 [@bip340; @bip341; @bip342], a single coin can hide a whole tree of alternative
spending conditions — a hash lock, a multisignature, a time lock — and reveal only the
branch that is actually used. Researchers are now studying proposed extensions, such as
covenants that restrict *how* a coin may be spent next, on a public test network called
Bitcoin Inquisition [@inquisition], where these proposals are already active.

Building such experiments by hand is error-prone. Every spend requires the script tree,
a Merkle proof called the control block, a signature over a carefully assembled
message, and a witness stack in exactly the right order. A single wrong byte produces a
rejected transaction with little explanation. `btcaaron` is a Python library that lets
a researcher state the intended conditions declaratively, build and sign the
transaction, and inspect every intermediate value, so that an on-chain experiment can be
rebuilt and re-checked by someone else.

# Statement of need

Research on Bitcoin script and covenant proposals increasingly rests on transactions
confirmed on a public network rather than on argument alone. For that evidence to be
checkable, the construction must be reproducible: another person needs to regenerate
the same script, the same signature message and the same witness from a short program.
`btcaaron` targets three groups: protocol researchers who prototype covenant
constructions on Bitcoin Inquisition signet, developers learning Taproot script-path
spending, and educators who need worked examples that run against a real network.

The library provides (i) a declarative builder for Taproot trees (`.hashlock()`,
`.multisig()`, `.timelock()`, `.checksig()`, `.custom()`), (ii) script-path and key-path
spend builders that construct the control block and order witnesses automatically,
(iii) direct access to the raw BIP-341 signature-message preimage, (iv) an independent
implementation of the BIP-118 ANYPREVOUT signature message [@bip118], (v) the BIP-446
template hash [@bip446], and (vi) script templates for opcodes active on Bitcoin
Inquisition: `OP_CAT` [@bip347], `OP_CHECKSIGFROMSTACK` [@bip348],
`OP_CHECKTEMPLATEVERIFY` [@bip119] and `OP_INTERNALKEY`.

# State of the field

Several mature Python libraries handle Bitcoin transactions. `python-bitcoin-utils`
[@bitcoinutils] offers low-level construction of scripts and transactions, including
Taproot, and is designed for learning; `python-bitcoinlib` [@pythonbitcoinlib] provides
core data structures; `BitcoinLib` [@bitcoinlib] focuses on wallets and persistence; and
`embit` [@embit] targets descriptors, PSBT and hardware-wallet integration. In the
current releases we inspected (python-bitcoin-utils 0.7.3, python-bitcoinlib 0.12.2,
BitcoinLib 0.7.10, embit 0.8.0) we found no implementation of the BIP-118 signature
message, `OP_CHECKSIGFROMSTACK`, `OP_CHECKTEMPLATEVERIFY` or the BIP-446 template hash.

`btcaaron` builds on `python-bitcoin-utils` for key handling and serialization rather
than re-implementing them, and adds the layer that covenant research needs: declarative
script-path construction, exposed signature-message preimages, and the experimental
signature and template-hash algorithms. These components are experimental by nature —
they track draft proposals and test-network software — which is why they live in a
separate research-oriented package instead of being proposed to a general-purpose
library.

# Software design

The package separates building, spending and broadcasting. `TapTree` collects leaves
and produces a `TaprootProgram` that knows its address, leaves and control blocks. A
program's `.spend(label)` or `.keypath()` returns a `SpendBuilder` that takes inputs,
outputs and unlocking data, signs, and assembles the witness; signature ordering for
`OP_CHECKSIGADD` multisignatures and `nSequence` for relative time locks are set
automatically. Network access (block explorers, a local node over RPC) is isolated in a
`network` module so that construction and verification work offline.

For covenant work the key design choice is transparency. `sigmsg` returns the exact
preimage that a node hashes when it verifies a Taproot signature, so that experiments
can split it into fields, feed it to `OP_CHECKSIGFROMSTACK`, or detect which sighash
flag a signer used. `bip118` implements the ANYPREVOUT message (`Msg118`/`Ext118`)
from the specification, and `templatehash` implements BIP-446, cross-checked against the
Bitcoin Inquisition v29.4 implementation. `RawScript` and `tapmath` let users write
arbitrary tapscript, including opcodes that the underlying library does not name, and
still compute leaf hashes, Merkle paths and tweaked keys. Programs and
transactions provide an `.explain()` method, and programs a `.visualize()` tree view,
that show what was built and why, which supports teaching use.

The repository contains 144 automated tests (5 skipped when no network is available),
including signature-message tests and the reproduction of TXIDs of previously confirmed
testnet transactions; continuous integration runs them on Python 3.10–3.12. An API
reference generated from the docstrings is in `docs/API.md`.

# Research impact statement

`btcaaron` is the construction and verification layer for a series of on-chain covenant
experiments on Bitcoin Inquisition signet. Its `examples/` directory and companion
repositories reproduce: output and input binding with `OP_CAT` and
`OP_CHECKSIGFROMSTACK`, and an eltoo-style [@eltoo] state chain built from a
`OP_CHECKSIGFROMSTACK` delegation ladder with `OP_CHECKTEMPLATEVERIFY` settlement
[@zhang2026parity]; ANYPREVOUT signing from scratch with an on-chain rebinding proof
[@zhang2026apo]; and a six-transaction eltoo state chain using ANYPREVOUT
[@zhang2026eltoo]. Each package lists the confirmed transaction IDs and a script that
checks them without private keys. Outside contributors have extended the library
(support for arbitrary leaf counts, duplicate-label checks, documentation) and reported
cross-node test results.

# AI usage disclosure

<!-- DRAFT for Aaron to correct. Evidence from git trailers: "Made-with: Cursor" on 5 commits
(2026-03-22 to 2026-03-31: Inquisition templates, BIP-118 sighash, INQUISITION.md, Braidpool
example); "Co-Authored-By: Claude" on 6 commits (Opus 4.6, 4.8, 5.5; 2026-03 to 2026-10:
reproduction packages, BIP-446, LICENSE, JOSS prep). Earlier commits (2025-08 to 2026-02,
including the TapTree/SpendBuilder core) carry no trailer — please state what you used there.
Remove anything that is not accurate; add OpenAI Codex/ChatGPT if you used them. -->

Generative AI coding assistants were used during development: Cursor (agent mode, with the
models it provided at the time) and Anthropic Claude via Claude Code (Claude Opus 4.6, 4.8 and
5.5). They were used for code generation and refactoring of library modules (including the
Bitcoin Inquisition script templates and the BIP 118 and BIP 446 hash implementations), test
scaffolding, documentation (README, `INQUISITION.md`, example READMEs, the generated API
reference) and for drafting and copy-editing this paper. AI tools were not used to decide
the design of the API, the choice of experiments, or the correctness criteria.

The author designed the API (the declarative `TapTree` / `TaprootProgram` / `SpendBuilder`
split and the exposure of signature-message preimages), defined every on-chain experiment,
and validated the code against external ground truth rather than against AI output: the
BIP test vectors, the Bitcoin Inquisition reference implementation, and transactions that
were broadcast and confirmed on testnet and Inquisition signet, whose TXIDs are reproduced by
the test suite. The author reviewed, edited and takes responsibility for all AI-assisted code,
documentation and text.

# Acknowledgements

Early development of `btcaaron` was supported by a grant from OpenSats. We thank the
contributors to `btcaaron` and the maintainers of Bitcoin Inquisition and
`python-bitcoin-utils`.

# References
