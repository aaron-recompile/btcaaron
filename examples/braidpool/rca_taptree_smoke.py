"""
Stage C — One Taproot tree, three leaves (RCA-shaped demo, not full protocol):

  * ``ctv_uhpo`` — multi-output OP_CHECKTEMPLATEVERIFY (UHPO split)
  * ``apo_update`` — BIP118 ``<0x01||xonly> OP_CHECKSIG`` (Eltoo-style update path)
  * ``csv_escape`` — CSV + CHECKSIG (timeout / solo-style path)

Each path is exercised separately: ``--fund`` then ``--spend ctv|apo|csv``.

**One funded UTXO is spent exactly once** — the first successful ``--spend`` consumes it.
To exercise **another** leaf on-chain, run ``--fund`` again (same tree shape, new coins).

**CSV path** needs the fund UTXO **confirmed** and depth for relative locktime. If ``--spend csv`` fails, wait and retry.

Prereqs: ``CAT_DEMO_WIF``, Inquisition RPC, wallet ``lab`` loaded.

From the **btcaaron repository root**::

    PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --fund
    PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --spend ctv
    PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --spend apo
    PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --spend csv

Verify::

    btcrun inq trace <txid>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_BRAIDPOOL_DIR = os.path.abspath(os.path.dirname(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_BRAIDPOOL_DIR, "..", ".."))
for _p in (_REPO_ROOT, _BRAIDPOOL_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import load_local_env  # noqa: F401

from braidpool_config import rpc as _node_rpc

from btcaaron import Key, TapTree, inq_ctv_script, inq_ctv_template_hash_for_outputs, wallet_send_sats
from template_common import (
    broadcast_or_raise,
    default_change_address,
    find_template_utxo_or_exit,
    fund_address,
    print_setup,
    read_txid_hint,
)

FUND_SATS = 50_000
DEFAULT_FEE_SATS = 3000
CSV_BLOCKS = 2
SPEND_FEE_SATS = 3000

DEMO_KEY_WIF = os.environ.get("CAT_DEMO_WIF", "")
if not DEMO_KEY_WIF:
    raise ValueError("Set CAT_DEMO_WIF (e.g. in repo root .env)")
key = Key.from_wif(DEMO_KEY_WIF)

_BASE = os.path.join(os.path.dirname(__file__), ".rca_taptree")
FUND_TXID_FILE = _BASE + "_fund_txid"
STATE_JSON = _BASE + "_state.json"
APO_REBIND_STATE_JSON = _BASE + "_apo_rebind_state.json"
APO_REBIND_SATS = 50_000
APO_REBIND_FEE = 3000


def _uhpo_splits(fee_sats: int) -> tuple[int, int, int]:
    total_out = FUND_SATS - fee_sats
    if total_out <= 0:
        raise ValueError("fee_sats must be < FUND_SATS")
    a = total_out * 50 // 100
    b = total_out * 30 // 100
    c = total_out - a - b
    return (a, b, c)


def _rpc_wallet():
    from braidpool_config import rpc_wallet

    return rpc_wallet


def _get_script_pubkey_hex(addr: str) -> str:
    return _rpc_wallet()("getaddressinfo", addr)["scriptPubKey"]


def build_apo_only_program():
    return TapTree(internal_key=key, network="signet").bip118_checksig(key, label="apo_rebind").build()


def build_rca_program(outputs: list[tuple[int, str]]) -> tuple[object, bytes]:
    template_hash = inq_ctv_template_hash_for_outputs(outputs)
    ctv_leaf = inq_ctv_script(template_hash)
    program = (
        TapTree(internal_key=key, network="signet")
        .custom(ctv_leaf, label="ctv_uhpo", unlock_hint="OP_CHECKTEMPLATEVERIFY UHPO split")
        .bip118_checksig(key, label="apo_update")
        .timelock(blocks=CSV_BLOCKS, then=key, label="csv_escape")
        .build()
    )
    return program, template_hash


def do_fund(fee_sats: int) -> None:
    uh = _uhpo_splits(fee_sats)
    rpc = _rpc_wallet()
    addrs = [rpc("getnewaddress", "", "bech32m") for _ in range(3)]
    rows = []
    outputs: list[tuple[int, str]] = []
    for addr, sats in zip(addrs, uh):
        spk = _get_script_pubkey_hex(addr)
        rows.append({"address": addr, "sats": sats, "scriptPubKey": spk})
        outputs.append((sats, spk))

    program, template_hash = build_rca_program(outputs)
    state = {
        "outputs": rows,
        "template_hash_hex": template_hash.hex(),
        "p2tr_address": program.address,
        "fee_sats": fee_sats,
        "fund_sats": FUND_SATS,
        "csv_blocks": CSV_BLOCKS,
        "leaves": ["ctv_uhpo", "apo_update", "csv_escape"],
    }
    with open(STATE_JSON, "w") as f:
        json.dump(state, f, indent=2)

    txid = fund_address(program.address, FUND_TXID_FILE, fund_sats=FUND_SATS)
    print(f"Fund TxID: {txid}")
    print(f"P2TR (3 leaves): {program.address}")
    print(f"Template hash (CTV): {template_hash.hex()}")
    print(f"Leaves: ctv_uhpo | apo_update | csv_escape (CSV relative blocks={CSV_BLOCKS})")
    print(
        "Note: one UTXO → one path. After any successful --spend, fund again to try another leaf."
    )


def _load_state() -> dict:
    if not os.path.exists(STATE_JSON):
        print("No state. Run --fund first.")
        sys.exit(1)
    with open(STATE_JSON) as f:
        return json.load(f)


def _program_from_state(state: dict):
    outputs = [(int(o["sats"]), o["scriptPubKey"]) for o in state["outputs"]]
    program, _ = build_rca_program(outputs)
    return program


def do_spend_ctv(txid_arg: str | None) -> None:
    state = _load_state()
    program = _program_from_state(state)
    txid_hint = read_txid_hint(txid_arg, FUND_TXID_FILE)
    utxo = find_template_utxo_or_exit(program.address, txid_hint)
    txid, vout, sats = utxo
    b = program.spend("ctv_uhpo").from_utxo(txid, vout, sats=sats).sequence(0xFFFFFFFF)
    for row in state["outputs"]:
        b = b.to(row["address"], int(row["sats"]))
    tx = b.unlock_with([]).build()
    out = broadcast_or_raise(tx.hex)
    print(f"Reveal (CTV) TxID: {out}")


def do_spend_apo(txid_arg: str | None) -> None:
    state = _load_state()
    program = _program_from_state(state)
    change = default_change_address()
    txid_hint = read_txid_hint(txid_arg, FUND_TXID_FILE)
    utxo = find_template_utxo_or_exit(program.address, txid_hint)
    txid, vout, sats = utxo
    if sats <= SPEND_FEE_SATS:
        raise ValueError("Input too small for fee")
    tx = (
        program.spend("apo_update")
        .from_utxo(txid, vout, sats=sats)
        .to(change, sats - SPEND_FEE_SATS)
        .sign(key)
        .build()
    )
    out = broadcast_or_raise(tx.hex)
    print(f"Reveal (APO) TxID: {out} (fee_sats={SPEND_FEE_SATS})")


def _utxos_from_fund_txids(address: str, fund_txids: list[str]) -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    for txid in fund_txids:
        raw = _node_rpc("getrawtransaction", txid, True)
        for vo in raw.get("vout", []):
            if vo.get("scriptPubKey", {}).get("address") != address:
                continue
            vout = int(vo["n"])
            sats = int(round(float(vo["value"]) * 1e8))
            go = None
            try:
                go = _node_rpc("gettxout", txid, vout, True)
            except Exception:
                try:
                    go = _node_rpc("gettxout", txid, vout)
                except Exception:
                    go = None
            if go is not None:
                out.append((txid, vout, sats))
            break
    return sorted(out, key=lambda x: (x[0], x[1]))


def _list_utxos_for_address(address: str) -> list[tuple[str, int, int]]:
    try:
        _node_rpc("scantxoutset", "abort")
    except Exception:
        pass
    scan = _node_rpc("scantxoutset", "start", json.dumps([f"addr({address})"]))
    out = []
    for u in scan.get("unspents", []):
        amt = u.get("amount")
        if amt is None:
            continue
        sats = int(round(float(amt) * 1e8))
        out.append((u["txid"], int(u["vout"]), sats))
    return sorted(out, key=lambda x: (x[0], x[1]))


def _apo_rebind_utxos(addr: str, fund_txids: list[str]) -> list[tuple[str, int, int]]:
    cands: list[tuple[str, int, int]] = []
    cands.extend(_utxos_from_fund_txids(addr, fund_txids))
    cands.extend(_list_utxos_for_address(addr))
    seen: set[tuple[str, int]] = set()
    uniq: list[tuple[str, int, int]] = []
    for u in sorted(cands, key=lambda x: (x[0], x[1])):
        k = (u[0], u[1])
        if k in seen:
            continue
        seen.add(k)
        if abs(u[2] - APO_REBIND_SATS) <= 1:
            uniq.append(u)
    return uniq


def do_fund_apo_rebind() -> None:
    program = build_apo_only_program()
    txid1 = wallet_send_sats(_rpc_wallet(), program.address, APO_REBIND_SATS)
    txid2 = wallet_send_sats(_rpc_wallet(), program.address, APO_REBIND_SATS)
    state = {
        "mode": "apo_rebind",
        "p2tr_address": program.address,
        "fund_txids": [txid1, txid2],
        "fund_sats_each": APO_REBIND_SATS,
        "leaf": "apo_rebind",
    }
    with open(APO_REBIND_STATE_JSON, "w") as f:
        json.dump(state, f, indent=2)
    print(f"APO-rebind fund 1 TxID: {txid1}")
    print(f"APO-rebind fund 2 TxID: {txid2}")
    print(f"P2TR (APO-only, same address twice): {program.address}")
    print("Next: PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --spend-apo-rebind")


def do_spend_apo_rebind() -> None:
    if not os.path.exists(APO_REBIND_STATE_JSON):
        print("No APO-rebind state. Run --fund-apo-rebind first.")
        sys.exit(1)
    with open(APO_REBIND_STATE_JSON) as f:
        st = json.load(f)
    addr = st["p2tr_address"]
    program = build_apo_only_program()
    if program.address != addr:
        raise RuntimeError("APO-only program address mismatch; use same CAT_DEMO_WIF as fund.")

    fund_txids = list(st.get("fund_txids") or [])
    utxos = _apo_rebind_utxos(addr, fund_txids)
    if len(utxos) < 2:
        print(
            f"Need 2 unspent outputs of ~{APO_REBIND_SATS} sats at {addr}; got {len(utxos)}."
        )
        print(
            "If one fund tx is still 0-conf, wait for a block or retry — "
            "fund txids from state must still be unspent."
        )
        sys.exit(1)
    u1, u2 = utxos[0], utxos[1]
    change = default_change_address()
    out_sats = APO_REBIND_SATS - APO_REBIND_FEE
    if out_sats <= 0:
        raise ValueError("fee too large")

    tx1 = (
        program.spend("apo_rebind")
        .from_utxo(u1[0], u1[1], sats=u1[2])
        .to(change, out_sats)
        .sign(key)
        .build()
    )
    stack = tx1._tx.witnesses[0].stack
    if len(stack) != 3:
        raise RuntimeError(f"expected 3 witness items, got {len(stack)}")

    def _wit_hex(x):
        if isinstance(x, str):
            return x
        if isinstance(x, (bytes, bytearray)):
            return bytes(x).hex()
        return x.hex()

    wit = [_wit_hex(stack[i]) for i in range(3)]

    tx2 = (
        program.spend("apo_rebind")
        .from_utxo(u2[0], u2[1], sats=u2[2])
        .to(change, out_sats)
        .unlock_with(wit)
        .build()
    )

    out1 = broadcast_or_raise(tx1.hex)
    out2 = broadcast_or_raise(tx2.hex)
    print("APO rebind: same signature bytes reused on a different prevout (BIP118).")
    print(f"  Spend UTXO1 (signed): {out1}")
    print(f"  Spend UTXO2 (reused witness): {out2}")


def do_spend_csv(txid_arg: str | None) -> None:
    state = _load_state()
    program = _program_from_state(state)
    change = default_change_address()
    txid_hint = read_txid_hint(txid_arg, FUND_TXID_FILE)
    utxo = find_template_utxo_or_exit(program.address, txid_hint)
    txid, vout, sats = utxo
    if sats <= SPEND_FEE_SATS:
        raise ValueError("Input too small for fee")
    tx = (
        program.spend("csv_escape")
        .from_utxo(txid, vout, sats=sats)
        .to(change, sats - SPEND_FEE_SATS)
        .sign(key)
        .build()
    )
    out = broadcast_or_raise(tx.hex)
    print(f"Reveal (CSV) TxID: {out} (fee_sats={SPEND_FEE_SATS})")
    print(
        f"Note: CSV requires fund tx confirmed + ~{state.get('csv_blocks', CSV_BLOCKS)} "
        "blocks depth; if rejected, wait and retry."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RCA-shaped 3-leaf TapTree smoke (CTV + APO + CSV)")
    parser.add_argument("--fund", action="store_true", help="Create state + fund P2TR")
    parser.add_argument(
        "--fund-apo-rebind",
        action="store_true",
        help="Fund APO-only P2TR twice (same address) for BIP118 signature reuse demo",
    )
    parser.add_argument(
        "--spend-apo-rebind",
        action="store_true",
        help="Broadcast two APO spends: sign for first UTXO, reuse witness for second",
    )
    parser.add_argument(
        "--fee-sats",
        type=int,
        default=DEFAULT_FEE_SATS,
        help="CTV template fee budget (fund only); default %(default)s",
    )
    parser.add_argument(
        "--spend",
        choices=("ctv", "apo", "csv"),
        help="Spend via one script path (one UTXO one spend; --fund again for another leaf)",
    )
    parser.add_argument("txid_hint", nargs="?", default=None, help="Optional fund txid filter")
    args = parser.parse_args()

    if args.fund_apo_rebind:
        do_fund_apo_rebind()
        return
    if args.spend_apo_rebind:
        do_spend_apo_rebind()
        return

    if args.fund:
        if args.fee_sats <= 0 or args.fee_sats >= FUND_SATS:
            parser.error("invalid --fee-sats")
        do_fund(args.fee_sats)
        return

    if args.spend:
        th = args.txid_hint
        if args.spend == "ctv":
            do_spend_ctv(th)
        elif args.spend == "apo":
            do_spend_apo(th)
        else:
            do_spend_csv(th)
        return

    print_setup(
        "RCA TapTree smoke — leaves: ctv_uhpo | apo_update | csv_escape",
        "(run --fund first)",
        "PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --fund\n"
        "PYTHONPATH=. python3 examples/braidpool/rca_taptree_smoke.py --spend ctv|apo|csv",
    )


if __name__ == "__main__":
    main()
