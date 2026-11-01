"""Generate reference vectors for BIP 118 and BIP 446 from Bitcoin Inquisition.

The expected values are computed by Bitcoin Inquisition's own Python test framework
(`test/functional/test_framework/script.py`: `TaprootSignatureMsg` with
`KEY_VERSION_ANYPREVOUT`, and `TemplateMsg`), not by btcaaron. The output is a fixed
JSON file that btcaaron's tests compare against, so the tests need no Inquisition
checkout at run time.

Usage:
    python tools/gen_inquisition_vectors.py <path-to-bitcoin-inquisition>/test/functional \
        > tests/vectors/inquisition_v29.4_vectors.json
"""

import json
import random
import sys

sys.path.insert(0, sys.argv[1])

from test_framework.key import TaggedHash  # noqa: E402
from test_framework.messages import COutPoint, CTransaction, CTxIn, CTxOut  # noqa: E402
from test_framework.script import (  # noqa: E402
    KEY_VERSION_ANYPREVOUT,
    TaprootSignatureMsg,
    TemplateMsg,
)

SEED = 20261101
N_TEMPLATE = 40
N_APO = 48

rng = random.Random(SEED)


def rbytes(n):
    return bytes(rng.getrandbits(8) for _ in range(n))


def random_spk():
    kind = rng.choice(["p2tr", "p2wpkh", "p2wsh", "p2pkh", "op_return"])
    if kind == "p2tr":
        return b"\x51\x20" + rbytes(32)
    if kind == "p2wpkh":
        return b"\x00\x14" + rbytes(20)
    if kind == "p2wsh":
        return b"\x00\x20" + rbytes(32)
    if kind == "p2pkh":
        return b"\x76\xa9\x14" + rbytes(20) + b"\x88\xac"
    data = rbytes(rng.randint(0, 40))
    return b"\x6a" + bytes([len(data)]) + data


def random_tx(n_in, n_out):
    tx = CTransaction()
    tx.version = rng.choice([1, 2, 3])
    tx.nLockTime = rng.choice([0, rng.getrandbits(32)])
    for _ in range(n_in):
        txin = CTxIn(COutPoint(rng.getrandbits(256), rng.randint(0, 10)))
        txin.nSequence = rng.choice([0xFFFFFFFF, 0xFFFFFFFD, 0, rng.getrandbits(32)])
        tx.vin.append(txin)
    for _ in range(n_out):
        tx.vout.append(CTxOut(rng.randint(0, 21_000_000 * 100_000_000), random_spk()))
    return tx


def random_annex():
    return None if rng.random() < 0.5 else b"\x50" + rbytes(rng.randint(0, 40))


def tx_record(tx):
    return {
        "tx_hex": tx.serialize_without_witness().hex(),
        "version": tx.version,
        "locktime": tx.nLockTime,
        "sequences": [i.nSequence for i in tx.vin],
        "outputs": [[o.nValue, o.scriptPubKey.hex()] for o in tx.vout],
    }


template_cases = []
for _ in range(N_TEMPLATE):
    tx = random_tx(rng.randint(1, 4), rng.randint(1, 4))
    idx = rng.randrange(len(tx.vin))
    annex = random_annex()
    msg = TemplateMsg(tx, idx, annex)
    template_cases.append({
        **tx_record(tx),
        "input_index": idx,
        "annex": annex.hex() if annex is not None else None,
        "expected_msg": msg.hex(),
        "expected_hash": TaggedHash("TemplateHash", msg).hex(),
    })

apo_cases = []
hash_types = [0x41, 0x42, 0x43, 0xC1, 0xC2, 0xC3]
for k in range(N_APO):
    hash_type = hash_types[k % len(hash_types)]
    n_in = rng.randint(1, 4)
    n_out = rng.randint(1, 4)
    tx = random_tx(n_in, n_out)
    idx = rng.randrange(n_in)
    if (hash_type & 0x03) == 0x03 and idx >= n_out:
        idx = rng.randrange(min(n_in, n_out))  # SIGHASH_SINGLE with a matching output
    spent = [CTxOut(rng.randint(0, 21_000_000 * 100_000_000), random_spk()) for _ in range(n_in)]
    spent[idx].scriptPubKey = b"\x51\x20" + rbytes(32)  # the input being signed is a P2TR script path
    leaf = b"\x21\x01" + rbytes(32) + b"\xac"  # <0x01||xonly> OP_CHECKSIG, a BIP 118 key
    annex = random_annex()
    msg = TaprootSignatureMsg(
        tx, spent, hash_type, idx,
        scriptpath=True, leaf_script=leaf, annex=annex, key_ver=KEY_VERSION_ANYPREVOUT,
    )
    apo_cases.append({
        **tx_record(tx),
        "spent": [[u.nValue, u.scriptPubKey.hex()] for u in spent],
        "input_index": idx,
        "hash_type": hash_type,
        "leaf_script": leaf.hex(),
        "annex": annex.hex() if annex is not None else None,
        "expected_msg": msg.hex(),
        "expected_sighash": TaggedHash("TapSighash", msg).hex(),
    })

json.dump({
    "source": "Bitcoin Inquisition v29.4-inq (3db09a1b58), test/functional/test_framework/script.py",
    "generator": "tools/gen_inquisition_vectors.py",
    "seed": SEED,
    "template_hash": template_cases,
    "bip118": apo_cases,
}, sys.stdout, indent=1)
sys.stdout.write("\n")
