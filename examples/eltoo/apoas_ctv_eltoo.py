"""
LN-Symmetry (eltoo) with SIGHASH_ANYPREVOUTANYSCRIPT (BIP 118) + OP_CHECKTEMPLATEVERIFY (BIP 119).

Same 3-round Alice/Bob/Carol scenario and the same run shape as th_csfs_ik_eltoo.py (Delving /t/3012),
so the APO column of the comparison also shows a newer state replacing a published older one:

    UPDATE(0)   = OP_1 OP_CHECKSIG                                                (2 B)
    UPDATE(n>0) = <TL(n)> OP_CHECKLOCKTIMEVERIFY OP_DROP OP_1 OP_CHECKSIG         (9 B)
    SETTLE(n)   = <ctv_hash(n)> OP_CHECKTEMPLATEVERIFY                            (34 B)
    TL(n)       = 500000000 + n

    funding output = tr(K, UPDATE(0))
    state-n output = tr(K, {UPDATE(n+1), SETTLE(n)})

The 1-byte public key 0x01 (OP_1) means "the taproot internal key, with BIP 118 semantics".
Update n carries nLockTime = TL(n) and a 0xc1 signature (ALL | ANYPREVOUTANYSCRIPT), which commits
to neither the outpoint, nor the spent amount and scriptPubKey, nor the tapleaf. So one signature
spends ANY earlier state, including from a different leaf; CLTV is the ratchet that stops an older
update from spending a newer state. Settlement needs no signature: CTV fixes the payout outputs and
the nSequence (BIP 68 shared_delay), so the other side has time to publish a newer update.

Differences from the earlier APO run (/t/2413), which used 0x41 and could only update in sequence:
  - 0xc1 instead of 0x41, so the signature is not tied to the spent scriptPubKey and can skip states;
  - CLTV state numbers in the update leaf, as in the eltoo paper;
  - updates are all signed before any state output exists.

PoC scope: K is a single key (no MuSig2), no HTLCs, nVersion 2, fees come out of the state value.

Run (Inquisition signet, wallet "lab"):
  python3 examples/eltoo/apoas_ctv_eltoo.py --setup      # sign U1, U2, U3 off-chain
  python3 examples/eltoo/apoas_ctv_eltoo.py --fund
  python3 examples/eltoo/apoas_ctv_eltoo.py --stale      # publish old state U1
  python3 examples/eltoo/apoas_ctv_eltoo.py --checks-s1  # testmempoolaccept checks on S1
  python3 examples/eltoo/apoas_ctv_eltoo.py --rebind     # U3 (signed in --setup) spends S1
  python3 examples/eltoo/apoas_ctv_eltoo.py --checks-s3
  python3 examples/eltoo/apoas_ctv_eltoo.py --checks-s3-late   # after SHARED_DELAY blocks
  python3 examples/eltoo/apoas_ctv_eltoo.py --settle
"""
import argparse
import hashlib
import json
import os
import struct
import sys
import time

_ELTOO_DIR = os.path.abspath(os.path.dirname(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_ELTOO_DIR, "..", ".."))
for _p in (_REPO_ROOT, _ELTOO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import load_local_env  # noqa: F401

from opcodes import OP_1, OP_CHECKSIG, OP_CHECKTEMPLATEVERIFY, OP_DROP, build_script, push_bytes
from btcaaron import Key, RawScript, TapTree

OP_CHECKLOCKTIMEVERIFY = 0xB1
SIGHASH_ALL_APOAS = 0xC1

# ---------------------------------------------------------------------------
# Scenario (same numbers as the TEMPLATEHASH run)
# ---------------------------------------------------------------------------
TX_VERSION = 2
UPDATE_SEQUENCE = 0xFFFFFFFD          # not final, so CLTV is enforceable
SHARED_DELAY = 3                      # settlement nSequence: BIP68 relative delay in blocks
FUND_SATS = 103_000
STATE_SATS = {1: 102_500, 2: 102_000, 3: 101_500}
PAYOUTS = {
    1: {"alice": 50_000, "bob": 30_000, "carol": 20_000},
    2: {"alice": 45_000, "bob": 35_000, "carol": 20_000},
    3: {"alice": 40_000, "bob": 35_000, "carol": 25_000},
}

_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_DIR, ".apoas_eltoo_state.json")

DEMO_KEY_WIF = os.environ.get("CAT_DEMO_WIF", "")
if not DEMO_KEY_WIF:
    raise ValueError("Set CAT_DEMO_WIF (signet WIF for channel key K)")


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
KEY_K = Key.from_wif(DEMO_KEY_WIF)


def _privkey():
    from secp256k1 import PrivateKey
    return PrivateKey(K_SECRET, raw=True)


def TL(n: int) -> int:
    return 500_000_000 + n


# ---------------------------------------------------------------------------
# Hashes: BIP 118 (ANYPREVOUTANYSCRIPT) and BIP 119 (CTV)
# ---------------------------------------------------------------------------
def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _tagged(tag: str, msg: bytes) -> bytes:
    t = _sha256(tag.encode())
    return _sha256(t + t + msg)


def _cs(n: int) -> bytes:
    if n < 253:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    return b"\xfe" + struct.pack("<I", n)


def _sha_outputs(outputs) -> bytes:
    return _sha256(b"".join(struct.pack("<q", sats) + _cs(len(spk)) + spk for sats, spk in outputs))


def apoas_sighash(version: int, locktime: int, sequence: int, outputs) -> bytes:
    """TaggedHash("TapSighash", 0x00 || Msg118(0xc1) || Ext118(0xc1)), no annex.

    Msg118 for ANYPREVOUTANYSCRIPT omits the outpoint, the spent amount and scriptPubKey;
    Ext118 omits the tapleaf hash. What is left: version, locktime, outputs, nSequence."""
    msg = (bytes([SIGHASH_ALL_APOAS]) + struct.pack("<i", version) + struct.pack("<I", locktime)
           + _sha_outputs(outputs) + bytes([2]) + struct.pack("<I", sequence))
    ext = bytes([0x01]) + struct.pack("<I", 0xFFFFFFFF)        # key_version 1, no codeseparator
    return _tagged("TapSighash", b"\x00" + msg + ext)


def ctv_hash(version: int, locktime: int, sequences, outputs, input_index: int = 0) -> bytes:
    """BIP 119 DefaultCheckTemplateVerifyHash (no scriptSigs)."""
    return _sha256(struct.pack("<i", version) + struct.pack("<I", locktime)
                   + struct.pack("<I", len(sequences)) + _sha256(b"".join(struct.pack("<I", s) for s in sequences))
                   + struct.pack("<I", len(outputs)) + _sha_outputs(outputs)
                   + struct.pack("<I", input_index))


# ---------------------------------------------------------------------------
# Scripts and programs
# ---------------------------------------------------------------------------
def leaf_update(n: int) -> bytes:
    if n == 0:
        return bytes.fromhex(build_script(OP_1, OP_CHECKSIG))
    return bytes.fromhex(build_script(push_bytes(struct.pack("<I", TL(n))), OP_CHECKLOCKTIMEVERIFY, OP_DROP,
                                      OP_1, OP_CHECKSIG))


def leaf_settle(h: bytes) -> bytes:
    return bytes.fromhex(build_script(push_bytes(h), OP_CHECKTEMPLATEVERIFY))


def funding_program():
    return TapTree(internal_key=KEY_K, network="signet").custom(
        script=RawScript(leaf_update(0).hex()), label="update").build()


def state_program(n: int, settle_hash: bytes):
    return (TapTree(internal_key=KEY_K, network="signet")
            .custom(script=RawScript(leaf_update(n + 1).hex()), label="update")
            .custom(script=RawScript(leaf_settle(settle_hash).hex()), label="settle")
            ).build()


# ---------------------------------------------------------------------------
# Raw transaction serialization
# ---------------------------------------------------------------------------
def ser_tx(version, inputs, outputs, locktime, witnesses=None) -> bytes:
    """inputs = [(txid_hex, vout, sequence)], outputs = [(sats, spk_bytes)], witnesses = [[bytes,...]]"""
    body = _cs(len(inputs))
    for txid, vout, seq in inputs:
        body += bytes.fromhex(txid)[::-1] + struct.pack("<I", vout) + b"\x00" + struct.pack("<I", seq)
    body += _cs(len(outputs))
    for sats, spk in outputs:
        body += struct.pack("<q", sats) + _cs(len(spk)) + spk
    lt = struct.pack("<I", locktime)
    if witnesses is None:
        return struct.pack("<i", version) + body + lt
    wit = b""
    for stack in witnesses:
        wit += _cs(len(stack)) + b"".join(_cs(len(e)) + e for e in stack)
    return struct.pack("<i", version) + b"\x00\x01" + body + wit + lt


def txid_of(version, inputs, outputs, locktime) -> str:
    return hashlib.sha256(hashlib.sha256(ser_tx(version, inputs, outputs, locktime)).digest()).digest()[::-1].hex()


# ---------------------------------------------------------------------------
# RPC and state
# ---------------------------------------------------------------------------
def rpc(*a):
    from eltoo_config import rpc as _rpc
    return _rpc(*a)


def rpc_wallet(*a):
    from eltoo_config import rpc_wallet as _rw
    return _rw(*a)


def spk_of(addr: str) -> bytes:
    return bytes.fromhex(rpc("validateaddress", addr)["scriptPubKey"])


def load():
    with open(STATE_FILE) as f:
        return json.load(f)


def save(st):
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, indent=2)


def payout_outputs(st, n):
    return [(PAYOUTS[n][who], bytes.fromhex(st["payout_spk"][who])) for who in ("alice", "bob", "carol")]


def rebuild(st):
    progs = {0: funding_program()}
    for n in (1, 2, 3):
        progs[n] = state_program(n, bytes.fromhex(st["settle_hash"][str(n)]))
    return progs


# ---------------------------------------------------------------------------
# Transaction builders
# ---------------------------------------------------------------------------
def update_tx(st, progs, n: int, prev_state: int, prev_txid: str, prev_vout: int = 0):
    """Update n (signed in --setup) spending state `prev_state` (0 = funding) via its update leaf."""
    leaf = leaf_update(0 if prev_state == 0 else prev_state + 1)
    cb = bytes.fromhex(progs[prev_state].control_block("update"))
    sig = bytes.fromhex(st["update_sig"][str(n)])
    outs = [(STATE_SATS[n], bytes.fromhex(st["state_spk"][str(n)]))]
    ins = [(prev_txid, prev_vout, UPDATE_SEQUENCE)]
    raw = ser_tx(TX_VERSION, ins, outs, TL(n), [[sig, leaf, cb]])
    return raw.hex(), txid_of(TX_VERSION, ins, outs, TL(n))


def stale_update_tx(st, progs, k: int, prev_state: int, prev_txid: str, prev_sats: int):
    """A freshly K-signed 0xc1 update with nLockTime TL(k) that leaves a 500 sat fee, so the node
    reaches script execution (CLTV) instead of rejecting on fee/value first. (Replaying U_k itself
    onto a newer state cannot even pay a fee: its signed output is larger than the newer state.)"""
    leaf = leaf_update(prev_state + 1)
    cb = bytes.fromhex(progs[prev_state].control_block("update"))
    outs = [(prev_sats - 500, bytes.fromhex(st["payout_spk"]["alice"]))]
    sig = _privkey().schnorr_sign(apoas_sighash(TX_VERSION, TL(k), UPDATE_SEQUENCE, outs), "", raw=True)
    ins = [(prev_txid, 0, UPDATE_SEQUENCE)]
    return ser_tx(TX_VERSION, ins, outs, TL(k), [[sig + bytes([SIGHASH_ALL_APOAS]), leaf, cb]]).hex()


def settle_tx(st, progs, n: int, prev_txid: str, prev_vout: int = 0, outputs=None):
    leaf = leaf_settle(bytes.fromhex(st["settle_hash"][str(n)]))
    cb = bytes.fromhex(progs[n].control_block("settle"))
    outs = outputs or payout_outputs(st, n)
    ins = [(prev_txid, prev_vout, SHARED_DELAY)]
    raw = ser_tx(TX_VERSION, ins, outs, TL(n), [[leaf, cb]])
    return raw.hex(), txid_of(TX_VERSION, ins, outs, TL(n))


def tma(label: str, raw_hex: str, expect_ok: bool):
    r = rpc("testmempoolaccept", [raw_hex])[0]
    ok = r.get("allowed", False)
    verdict = "PASS" if ok == expect_ok else "UNEXPECTED"
    reason = r.get("reject-reason", "") or "accepted"
    print(f"  [{verdict}] {label}: allowed={ok} ({reason})")
    return {"label": label, "allowed": ok, "reason": reason, "expected_allowed": expect_ok, "verdict": verdict}


def broadcast(label: str, raw_hex: str) -> str:
    r = rpc("testmempoolaccept", [raw_hex])[0]
    if not r.get("allowed"):
        raise SystemExit(f"{label} rejected: {r.get('reject-reason')}")
    txid = rpc("sendrawtransaction", raw_hex)
    print(f"  {label} broadcast: {txid}")
    return txid


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------
def do_setup():
    st = {"created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "internal_key": KEY_K.xonly,
          "payout_addr": {}, "payout_spk": {}, "settle_hash": {}, "state_spk": {}, "state_addr": {},
          "update_sighash": {}, "update_sig": {}, "checks": []}
    for who in ("alice", "bob", "carol"):
        a = rpc_wallet("getnewaddress", f"apoas_{who}", "bech32m")
        st["payout_addr"][who] = a
        st["payout_spk"][who] = spk_of(a).hex()
    pk = _privkey()
    for n in (1, 2, 3):
        sh = ctv_hash(TX_VERSION, TL(n), [SHARED_DELAY], payout_outputs(st, n))
        st["settle_hash"][str(n)] = sh.hex()
        prog = state_program(n, sh)
        st["state_addr"][str(n)] = prog.address
        st["state_spk"][str(n)] = spk_of(prog.address).hex()
        d = apoas_sighash(TX_VERSION, TL(n), UPDATE_SEQUENCE, [(STATE_SATS[n], bytes.fromhex(st["state_spk"][str(n)]))])
        sig = pk.schnorr_sign(d, "", raw=True)
        assert pk.pubkey.schnorr_verify(d, sig, "", raw=True)
        st["update_sighash"][str(n)] = d.hex()
        st["update_sig"][str(n)] = (sig + bytes([SIGHASH_ALL_APOAS])).hex()
    st["funding_addr"] = funding_program().address
    save(st)
    print("=== setup: all three updates signed off-chain (before any state output exists) ===")
    print(f"internal key K: {KEY_K.xonly}")
    print(f"funding: {st['funding_addr']}  UPDATE(0) = {leaf_update(0).hex()}")
    for n in (1, 2, 3):
        print(f"state {n}: {STATE_SATS[n]} sat  {st['state_addr'][str(n)]}")
        print(f"   UPDATE({n + 1}) = {leaf_update(n + 1).hex()}  ({len(leaf_update(n + 1))} B)")
        print(f"   SETTLE({n}) = {leaf_settle(bytes.fromhex(st['settle_hash'][str(n)])).hex()}")
        print(f"   update {n} sig (0xc1) {st['update_sig'][str(n)]}")


def do_fund():
    st = load()
    txid = rpc_wallet("sendtoaddress", st["funding_addr"], f"{FUND_SATS / 1e8:.8f}", "", "", False, False, "null", "unset", False, 1)
    raw = rpc("getrawtransaction", txid, 1)
    vout = next(o["n"] for o in raw["vout"] if o["scriptPubKey"].get("address") == st["funding_addr"])
    st["fund"] = {"txid": txid, "vout": vout}
    save(st)
    print(f"fund: {txid}:{vout}  ({FUND_SATS} sat)")


def do_stale():
    st = load()
    progs = rebuild(st)
    raw, _ = update_tx(st, progs, 1, 0, st["fund"]["txid"], st["fund"]["vout"])
    st["u1"] = {"txid": broadcast("U1 (old state 1, spends funding)", raw), "raw": raw}
    save(st)


def do_checks_s1():
    st = load()
    progs = rebuild(st)
    s1 = st["u1"]["txid"]
    print("=== checks against state-1 output S1 (testmempoolaccept only) ===")
    raw = stale_update_tx(st, progs, 1, 1, s1, STATE_SATS[1])
    st["checks"].append(tma("nLockTime TL(1) update onto S1 (needs TL(2))", raw, False))
    raw, _ = update_tx(st, progs, 2, 1, s1)
    st["checks"].append(tma("U2 signature rebinds onto S1", raw, True))
    raw, _ = settle_tx(st, progs, 1, s1)
    st["checks"].append(tma("Settle 1 before shared_delay", raw, False))
    save(st)


def do_rebind():
    st = load()
    progs = rebuild(st)
    raw, _ = update_tx(st, progs, 3, 1, st["u1"]["txid"])
    st["u3"] = {"txid": broadcast("U3 (signed in --setup) spends S1, skipping state 2", raw), "raw": raw}
    save(st)


def do_checks_s3():
    st = load()
    progs = rebuild(st)
    s3 = st["u3"]["txid"]
    print("=== checks against state-3 output S3 (testmempoolaccept only) ===")
    raw = stale_update_tx(st, progs, 2, 3, s3, STATE_SATS[3])
    st["checks"].append(tma("nLockTime TL(2) update onto S3 (needs TL(4))", raw, False))
    raw, _ = settle_tx(st, progs, 3, s3)
    st["checks"].append(tma("Settle 3 before shared_delay", raw, False))
    save(st)


def do_checks_s3_late():
    """Run after SHARED_DELAY confirmations, so BIP68 no longer masks the script result."""
    st = load()
    progs = rebuild(st)
    s3 = st["u3"]["txid"]
    p = PAYOUTS[3]
    swapped = [(p["bob"], bytes.fromhex(st["payout_spk"]["alice"])), (p["alice"], bytes.fromhex(st["payout_spk"]["bob"])),
               (p["carol"], bytes.fromhex(st["payout_spk"]["carol"]))]
    raw, _ = settle_tx(st, progs, 3, s3, outputs=swapped)
    st["checks"].append(tma("Settle 3 with Alice/Bob amounts swapped", raw, False))
    save(st)


def do_settle():
    st = load()
    progs = rebuild(st)
    raw, _ = settle_tx(st, progs, 3, st["u3"]["txid"])
    st["settle3"] = {"txid": broadcast("Settle 3 (40k / 35k / 25k, no signature)", raw), "raw": raw}
    save(st)


def do_status():
    st = load()
    for k in ("fund", "u1", "u3", "settle3"):
        if k in st:
            tx = st[k]["txid"]
            try:
                info = rpc("getrawtransaction", tx, 1)
                wit = info["vin"][0].get("txinwitness", [])
                wbytes = sum(len(w) // 2 for w in wit)
                print(f"{k:8} {tx}  confirmations={info.get('confirmations', 0)}  vsize={info['vsize']}  "
                      f"weight={info['weight']}  witness_items={len(wit)} witness_bytes={wbytes}")
            except Exception as e:
                print(f"{k:8} {tx}  ({e})")
    for c in st.get("checks", []):
        print(f"check [{c['verdict']}] {c['label']}: allowed={c['allowed']} ({c['reason']})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for flag in ("setup", "fund", "stale", "checks-s1", "rebind", "checks-s3", "checks-s3-late", "settle", "status"):
        ap.add_argument(f"--{flag}", action="store_true")
    a = ap.parse_args()
    if a.setup: do_setup()
    elif a.fund: do_fund()
    elif a.stale: do_stale()
    elif a.checks_s1: do_checks_s1()
    elif a.rebind: do_rebind()
    elif a.checks_s3: do_checks_s3()
    elif a.checks_s3_late: do_checks_s3_late()
    elif a.settle: do_settle()
    elif a.status: do_status()
    else: ap.print_help()
