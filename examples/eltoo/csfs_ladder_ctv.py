"""
CSFS Ladder + CTV Settlement — Eltoo state chain with enforced payout.

v2 of the CSFS Ladder experiment. Key upgrade from v1:
  v1: R_2 signs a symbolic commitment (SHA256 of description) -> not enforced
  v2: R_2 signs the CTV template hash -> CTV enforces 3-output payout

This makes CSFS+CTV directly comparable to APO+CTV from our Delving Bitcoin post.

  APO+CTV:  APO handles state override, CTV handles settlement
  CSFS+CTV: CSFS ladder handles state progression, CTV handles settlement

Scenario (same as APO experiment and v1):
  State 0: Alice 50k, Bob 30k, Carol 20k
  State 1: Alice 45k, Bob 35k, Carol 20k
  State 2: Alice 40k, Bob 35k, Carol 25k

Script (42 bytes):
  <K_pub_32> CSFS VERIFY CSFS VERIFY CSFS VERIFY CSFS VERIFY CTV

Witness (12 data elements):
  [0]  ctv_hash          32B   CTV template hash (survives for CTV opcode)
  [1]  settle_sig_R2     64B   CSFS #4 sig
  [2]  ctv_hash          32B   CSFS #4 msg (R_2 signed the CTV hash)
  [3]  R2_pub            32B   CSFS #4 pub
  [4]  sig_R1_to_R2      64B   CSFS #3 sig
  [5]  R2_pub            32B   CSFS #3 msg
  [6]  R1_pub            32B   CSFS #3 pub
  [7]  sig_R0_to_R1      64B   CSFS #2 sig
  [8]  R1_pub            32B   CSFS #2 msg
  [9]  R0_pub            32B   CSFS #2 pub
  [10] sig_K_to_R0       64B   CSFS #1 sig
  [11] R0_pub            32B   CSFS #1 msg

Stack trace (top at top):
  initial:  12 items (witness [0]-[11])
  PUSH K + CSFS #1 + VERIFY:  K->R0 verified, 9 items left
  CSFS #2 + VERIFY:           R0->R1 verified, 6 items left
  CSFS #3 + VERIFY:           R1->R2 verified, 3 items left
  CSFS #4:                    R2 signed ctv_hash, pushes [OK], 2 items
  VERIFY:                     pop [OK], 1 item left = ctv_hash[0]
  CTV:                        check ctv_hash matches tx outputs -> pass

Run:
  PYTHONPATH=. python3 experiments/CSFS_LN_Symmetry_State_Binding_v2/code/csfs_ladder_ctv.py --fund
  PYTHONPATH=. python3 experiments/CSFS_LN_Symmetry_State_Binding_v2/code/csfs_ladder_ctv.py --delegate
  PYTHONPATH=. python3 experiments/CSFS_LN_Symmetry_State_Binding_v2/code/csfs_ladder_ctv.py --spend [--fee-sats 1000]
"""
import argparse
import hashlib
import json
import os
import struct
import sys

# Allow `python3 examples/eltoo/csfs_ladder_ctv.py` from the btcaaron repo root,
# and `python3 csfs_ladder_ctv.py` from inside this directory.
_ELTOO_DIR = os.path.abspath(os.path.dirname(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_ELTOO_DIR, "..", ".."))
for _p in (_REPO_ROOT, _ELTOO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import load_local_env  # noqa: F401

from opcodes import (
    OP_CHECKSIGFROMSTACK,
    OP_CHECKTEMPLATEVERIFY,
    OP_VERIFY,
    build_script,
    push_bytes,
)
from btcaaron import Key, RawScript, TapTree

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Payout amounts per state (in satoshis)
STATES = [
    {"label": "state_0", "alice": 50000, "bob": 30000, "carol": 20000},
    {"label": "state_1", "alice": 45000, "bob": 35000, "carol": 20000},
    {"label": "state_2", "alice": 40000, "bob": 35000, "carol": 25000},
]

FUND_AMOUNT_SATS = 101_000  # enough for 3-output settlement + fee
FEE_SATS = 1000

# File paths
_DIR = os.path.dirname(os.path.abspath(__file__))
FUND_TXID_FILE = os.path.join(_DIR, ".v2_fund_txid")
DELEGATION_FILE = os.path.join(_DIR, ".v2_delegations.json")
STATE_FILE = os.path.join(_DIR, ".v2_state.json")
ADDRS_FILE = os.path.join(_DIR, ".v2_payout_addrs.json")

# ---------------------------------------------------------------------------
# Key management (same as v1)
# ---------------------------------------------------------------------------

DEMO_KEY_WIF = os.environ.get("CAT_DEMO_WIF", "")
if not DEMO_KEY_WIF:
    raise ValueError("Set CAT_DEMO_WIF (signet WIF for channel root key K)")


def _wif_to_secret(wif: str) -> bytes:
    B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    b = 0
    for c in wif:
        b = b * 58 + B58.index(c)
    raw = b.to_bytes((b.bit_length() + 7) // 8 or 1, "big").lstrip(b"\x00")
    pad = 37 if len(raw) <= 37 else 38
    raw = (b"\x00" * (pad - len(raw))) + raw
    payload_len = 34 if len(raw) == 38 else 33
    chk = hashlib.sha256(hashlib.sha256(raw[:payload_len]).digest()).digest()[:4]
    assert raw[payload_len:] == chk
    return raw[1:33]


K_SECRET = _wif_to_secret(DEMO_KEY_WIF)


def _derive_state_secret(state_index: int) -> bytes:
    return hashlib.sha256(K_SECRET + f"state_{state_index}".encode()).digest()


def _get_all_keys():
    from secp256k1 import PrivateKey
    pk_k = PrivateKey(K_SECRET, raw=True)
    pub_k = pk_k.pubkey.serialize()[1:33]
    r_keys = []
    for i in range(len(STATES)):
        secret = _derive_state_secret(i)
        pk = PrivateKey(secret, raw=True)
        pub = pk.pubkey.serialize()[1:33]
        r_keys.append((pk, pub))
    return pk_k, pub_k, r_keys


# ---------------------------------------------------------------------------
# CTV hash computation (from ctv.py)
# ---------------------------------------------------------------------------

def _ser_compact_size(n: int) -> bytes:
    if n < 253:
        return struct.pack("B", n)
    if n < 0x10000:
        return struct.pack("<BH", 253, n)
    if n < 0x100000000:
        return struct.pack("<BI", 254, n)
    return struct.pack("<BQ", 255, n)


def _ser_string(s: bytes) -> bytes:
    return _ser_compact_size(len(s)) + s


def _ser_txout(n_value: int, script_pubkey: bytes) -> bytes:
    return struct.pack("<q", n_value) + _ser_string(script_pubkey)


def compute_ctv_hash(n_version, n_locktime, n_vin, sequences, n_vout,
                     outputs_serialized, n_in) -> bytes:
    """BIP119 DefaultCheckTemplateVerifyHash."""
    r = b""
    r += struct.pack("<i", n_version)
    r += struct.pack("<I", n_locktime)
    r += struct.pack("<I", n_vin)
    r += hashlib.sha256(sequences).digest()
    r += struct.pack("<I", n_vout)
    r += hashlib.sha256(outputs_serialized).digest()
    r += struct.pack("<I", n_in)
    return hashlib.sha256(r).digest()


def _get_script_pubkey(addr: str) -> bytes:
    from eltoo_config import rpc_wallet
    info = rpc_wallet("getaddressinfo", addr)
    return bytes.fromhex(info["scriptPubKey"])


def _compute_settlement_ctv_hash(payout_addrs: dict, state_index: int) -> bytes:
    """Compute CTV hash for the 3-output settlement of a given state."""
    state = STATES[state_index]

    # 3 outputs: Alice, Bob, Carol
    outputs_ser = b""
    outputs_ser += _ser_txout(state["alice"], _get_script_pubkey(payout_addrs["alice"]))
    outputs_ser += _ser_txout(state["bob"], _get_script_pubkey(payout_addrs["bob"]))
    outputs_ser += _ser_txout(state["carol"], _get_script_pubkey(payout_addrs["carol"]))

    seq = struct.pack("<I", 0xFFFFFFFF)

    return compute_ctv_hash(
        n_version=2,
        n_locktime=0,
        n_vin=1,
        sequences=seq,
        n_vout=3,
        outputs_serialized=outputs_ser,
        n_in=0,
    )


# ---------------------------------------------------------------------------
# Script & address construction
# ---------------------------------------------------------------------------

def _build_ladder_ctv_program():
    """Build Taproot program with CSFS ladder + CTV settlement."""
    _, pub_k, _ = _get_all_keys()

    # Script: <K_pub> CSFS VERIFY CSFS VERIFY CSFS VERIFY CSFS VERIFY CTV
    script_hex = build_script(
        push_bytes(pub_k),
        OP_CHECKSIGFROMSTACK,    # CSFS #1: K -> R0
        OP_VERIFY,
        OP_CHECKSIGFROMSTACK,    # CSFS #2: R0 -> R1
        OP_VERIFY,
        OP_CHECKSIGFROMSTACK,    # CSFS #3: R1 -> R2
        OP_VERIFY,
        OP_CHECKSIGFROMSTACK,    # CSFS #4: R2 -> ctv_hash
        OP_VERIFY,
        OP_CHECKTEMPLATEVERIFY,  # CTV: enforce output template
    )
    leaf_script = RawScript(script_hex)

    key_k = Key.from_wif(DEMO_KEY_WIF)
    program = (
        TapTree(internal_key=key_k, network="signet")
        .custom(script=leaf_script, label="ladder_ctv")
    ).build()

    return program


program = _build_ladder_ctv_program()
addr = program.address

# ---------------------------------------------------------------------------
# Phase 1: Fund
# ---------------------------------------------------------------------------

def do_fund():
    from eltoo_config import rpc_wallet

    _, pub_k, r_keys = _get_all_keys()

    # Generate 3 payout addresses (Alice, Bob, Carol)
    alice_addr = rpc_wallet("getnewaddress", "alice", "bech32m")
    bob_addr = rpc_wallet("getnewaddress", "bob", "bech32m")
    carol_addr = rpc_wallet("getnewaddress", "carol", "bech32m")

    payout_addrs = {"alice": alice_addr, "bob": bob_addr, "carol": carol_addr}
    with open(ADDRS_FILE, "w") as f:
        json.dump(payout_addrs, f, indent=2)

    print("=== CSFS Ladder + CTV Settlement: Fund (v2) ===")
    print(f"Channel root key K: {pub_k.hex()}")
    for i, (_, pub_r) in enumerate(r_keys):
        print(f"State {i} key R_{i}:   {pub_r.hex()}")
    print(f"Ladder+CTV address: {addr}")
    print()
    print("Taproot structure:")
    print("  Key path  -> K (cooperative close)")
    print("  Script    -> 3-hop CSFS ladder + CTV (state chain + enforced payout)")
    print()
    print("Payout addresses:")
    print(f"  Alice: {alice_addr}")
    print(f"  Bob:   {bob_addr}")
    print(f"  Carol: {carol_addr}")
    print()
    print("States:")
    for i, s in enumerate(STATES):
        print(f"  State {i}: alice:{s['alice']} bob:{s['bob']} carol:{s['carol']}")
    print()

    fund_btc = FUND_AMOUNT_SATS / 1e8
    txid = rpc_wallet(
        "sendtoaddress", addr, fund_btc,
        "", "", False, False, None, "unset", False, 1,
    )
    with open(FUND_TXID_FILE, "w") as f:
        f.write(txid)

    state_info = {
        "fund_txid": txid,
        "fund_amount_sats": FUND_AMOUNT_SATS,
        "address": addr,
        "root_key": pub_k.hex(),
        "state_keys": {f"R_{i}": pub_r.hex() for i, (_, pub_r) in enumerate(r_keys)},
        "payout_addrs": payout_addrs,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state_info, f, indent=2)

    print(f"Fund TxID: {txid}")
    print(f"Amount: {FUND_AMOUNT_SATS} sats")
    print("Next: --delegate")


# ---------------------------------------------------------------------------
# Phase 2: Delegate (off-chain)
# ---------------------------------------------------------------------------

def do_delegate():
    if not os.path.exists(ADDRS_FILE):
        print("No payout addresses. Run --fund first.")
        sys.exit(1)
    with open(ADDRS_FILE) as f:
        payout_addrs = json.load(f)

    pk_k, pub_k, r_keys = _get_all_keys()
    pk_r0, pub_r0 = r_keys[0]
    pk_r1, pub_r1 = r_keys[1]
    pk_r2, pub_r2 = r_keys[2]

    # Delegation chain: K -> R0 -> R1 -> R2
    sig_k_to_r0 = pk_k.schnorr_sign(pub_r0, "", raw=True)
    sig_r0_to_r1 = pk_r0.schnorr_sign(pub_r1, "", raw=True)
    sig_r1_to_r2 = pk_r1.schnorr_sign(pub_r2, "", raw=True)

    # Settlement: R_2 signs the CTV template hash for State 2
    ctv_hash = _compute_settlement_ctv_hash(payout_addrs, 2)
    settle_sig = pk_r2.schnorr_sign(ctv_hash, "", raw=True)

    delegations = {
        "chain": "K -> R_0 -> R_1 -> R_2 -> CTV(State 2)",
        "settlement_state": 2,
        "settlement_payout": STATES[2],
        "ctv_hash": ctv_hash.hex(),
        "hops": [
            {"from": "K", "to": "R_0", "signer_pub": pub_k.hex(),
             "delegatee_pub": pub_r0.hex(), "sig": sig_k_to_r0.hex()},
            {"from": "R_0", "to": "R_1", "signer_pub": pub_r0.hex(),
             "delegatee_pub": pub_r1.hex(), "sig": sig_r0_to_r1.hex()},
            {"from": "R_1", "to": "R_2", "signer_pub": pub_r1.hex(),
             "delegatee_pub": pub_r2.hex(), "sig": sig_r1_to_r2.hex()},
        ],
        "settlement_sig": settle_sig.hex(),
        "settlement_signer": pub_r2.hex(),
        "payout_addrs": payout_addrs,
    }
    with open(DELEGATION_FILE, "w") as f:
        json.dump(delegations, f, indent=2)

    print("=== CSFS Ladder + CTV Settlement: Delegate (v2) ===")
    print()
    print("3-hop delegation chain (all OFF-CHAIN):")
    print(f"  Hop 1: K   ({pub_k.hex()[:12]}...) -> R_0 ({pub_r0.hex()[:12]}...)")
    print(f"  Hop 2: R_0 ({pub_r0.hex()[:12]}...) -> R_1 ({pub_r1.hex()[:12]}...)")
    print(f"  Hop 3: R_1 ({pub_r1.hex()[:12]}...) -> R_2 ({pub_r2.hex()[:12]}...)")
    print(f"  Settle: R_2 signs CTV hash for State 2")
    print()
    print(f"CTV hash: {ctv_hash.hex()}")
    print(f"Settlement: alice:{STATES[2]['alice']} bob:{STATES[2]['bob']} carol:{STATES[2]['carol']}")
    print(f"  Alice -> {payout_addrs['alice']}")
    print(f"  Bob   -> {payout_addrs['bob']}")
    print(f"  Carol -> {payout_addrs['carol']}")
    print()
    print(f"Saved to: {DELEGATION_FILE}")
    print("Next: --spend")


# ---------------------------------------------------------------------------
# Phase 3: Spend — 3-output CTV settlement
# ---------------------------------------------------------------------------

def _find_utxo_via_txid(txid):
    from eltoo_config import rpc
    try:
        raw = rpc("getrawtransaction", txid, 1)
    except Exception:
        return None
    if not raw:
        return None
    for out in raw.get("vout", []):
        if out.get("scriptPubKey", {}).get("address") == addr:
            return txid, out["n"], int(out["value"] * 1e8)
    return None


def do_spend(txid_arg=None, fee_sats=FEE_SATS):
    from eltoo_config import rpc, rpc_wallet

    if not os.path.exists(DELEGATION_FILE):
        print("No delegation chain. Run --delegate first.")
        sys.exit(1)
    with open(DELEGATION_FILE) as f:
        deleg = json.load(f)

    payout_addrs = deleg["payout_addrs"]
    state = STATES[deleg["settlement_state"]]

    # Resolve UTXO
    utxo = None
    if txid_arg:
        utxo = _find_utxo_via_txid(txid_arg)
    elif os.path.exists(FUND_TXID_FILE):
        with open(FUND_TXID_FILE) as f:
            utxo = _find_utxo_via_txid(f.read().strip())
    if not utxo:
        try:
            rpc("scantxoutset", "abort")
        except Exception:
            pass
        scan = rpc("scantxoutset", "start", json.dumps([f"addr({addr})"]))
        unspents = scan.get("unspents", [])
        if not unspents:
            print("No UTXO. Run --fund first.")
            sys.exit(1)
        u = unspents[0]
        amt = u.get("value", u.get("amount"))
        utxo = u["txid"], u["vout"], int(float(amt) * 1e8)

    txid, vout, sats = utxo

    # Extract delegation data
    hop0 = deleg["hops"][0]
    hop1 = deleg["hops"][1]
    hop2 = deleg["hops"][2]
    ctv_hash_hex = deleg["ctv_hash"]
    settle_sig_hex = deleg["settlement_sig"]

    r0_pub = hop0["delegatee_pub"]
    r1_pub = hop1["delegatee_pub"]
    r2_pub = hop2["delegatee_pub"]

    # Build witness: 12 elements
    # [0]  ctv_hash         survives for CTV opcode
    # [1]  settle_sig_R2    CSFS #4 sig
    # [2]  ctv_hash         CSFS #4 msg (consumed by CSFS)
    # [3]  R2_pub           CSFS #4 pub
    # [4]  sig_R1_to_R2     CSFS #3 sig
    # [5]  R2_pub           CSFS #3 msg
    # [6]  R1_pub           CSFS #3 pub
    # [7]  sig_R0_to_R1     CSFS #2 sig
    # [8]  R1_pub           CSFS #2 msg
    # [9]  R0_pub           CSFS #2 pub
    # [10] sig_K_to_R0      CSFS #1 sig
    # [11] R0_pub           CSFS #1 msg
    witness = [
        ctv_hash_hex,        # [0]  survives for CTV
        settle_sig_hex,      # [1]  CSFS #4 sig
        ctv_hash_hex,        # [2]  CSFS #4 msg
        r2_pub,              # [3]  CSFS #4 pub
        hop2["sig"],         # [4]  CSFS #3 sig (R1->R2)
        r2_pub,              # [5]  CSFS #3 msg
        r1_pub,              # [6]  CSFS #3 pub
        hop1["sig"],         # [7]  CSFS #2 sig (R0->R1)
        r1_pub,              # [8]  CSFS #2 msg
        r0_pub,              # [9]  CSFS #2 pub
        hop0["sig"],         # [10] CSFS #1 sig (K->R0)
        r0_pub,              # [11] CSFS #1 msg
    ]

    # Build spend tx with 3 outputs (CTV-enforced)
    tx = (
        program.spend("ladder_ctv")
        .from_utxo(txid, vout, sats=sats)
        .to(payout_addrs["alice"], state["alice"])
        .to(payout_addrs["bob"], state["bob"])
        .to(payout_addrs["carol"], state["carol"])
        .sequence(0xFFFFFFFF)
        .unlock_with(witness)
        .build()
    )

    print("=== CSFS Ladder + CTV Settlement: Spend (v2) ===")
    print(f"Input:  {txid}:{vout} ({sats} sats)")
    print()
    print("Outputs (CTV-enforced):")
    print(f"  Alice: {state['alice']} sats -> {payout_addrs['alice']}")
    print(f"  Bob:   {state['bob']} sats -> {payout_addrs['bob']}")
    print(f"  Carol: {state['carol']} sats -> {payout_addrs['carol']}")
    print(f"  Fee:   {sats - state['alice'] - state['bob'] - state['carol']} sats")
    print()
    print(f"CTV hash: {ctv_hash_hex}")
    print()
    print("Ladder proof (3 hops + CTV settlement):")
    print(f"  CSFS #1: K   -> R_0  sig={hop0['sig'][:24]}...")
    print(f"  CSFS #2: R_0 -> R_1  sig={hop1['sig'][:24]}...")
    print(f"  CSFS #3: R_1 -> R_2  sig={hop2['sig'][:24]}...")
    print(f"  CSFS #4: R_2 -> CTV  sig={settle_sig_hex[:24]}...")
    print(f"  CTV:     enforce 3-output template")
    print()
    print(f"Witness: {len(witness)} data elements")
    total_bytes = sum(len(bytes.fromhex(w)) for w in witness)
    print(f"Witness data size: {total_bytes} bytes")
    print()

    test_result = rpc("testmempoolaccept", [tx.hex])
    if test_result and test_result[0].get("allowed"):
        print("testmempoolaccept: ALLOWED [OK]")
        reveal_txid = rpc("sendrawtransaction", tx.hex)
        print(f"Spend TxID: {reveal_txid}")

        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                st = json.load(f)
            st["spend_txid"] = reveal_txid
            st["settlement_state"] = 2
            with open(STATE_FILE, "w") as f:
                json.dump(st, f, indent=2)
    else:
        print("testmempoolaccept: REJECTED")
        print(json.dumps(test_result, indent=2))
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_setup():
    _, pub_k, r_keys = _get_all_keys()
    print("CSFS Ladder + CTV Settlement (v2)")
    print(f"  Root key K: {pub_k.hex()}")
    for i, (_, pub_r) in enumerate(r_keys):
        print(f"  State {i} R_{i}: {pub_r.hex()}")
    print(f"  Address:    {addr}")
    print()
    print("States:")
    for i, s in enumerate(STATES):
        print(f"  {i}: alice:{s['alice']} bob:{s['bob']} carol:{s['carol']}")
    print()
    print("Usage:")
    print("  --fund       Lock coins to ladder+CTV address")
    print("  --delegate   Build delegation chain + CTV hash (off-chain)")
    print("  --spend      Spend with ladder proof + CTV 3-output settlement")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSFS Ladder + CTV Settlement (v2)")
    parser.add_argument("--fund", action="store_true")
    parser.add_argument("--delegate", action="store_true")
    parser.add_argument("--spend", nargs="?", const="", default=None, metavar="TXID")
    parser.add_argument("--fee-sats", type=int, default=FEE_SATS)
    args = parser.parse_args()

    if args.fund:
        do_fund()
    elif args.delegate:
        do_delegate()
    elif args.spend is not None:
        txid_arg = args.spend if args.spend else None
        do_spend(txid_arg, fee_sats=args.fee_sats)
    else:
        print_setup()
