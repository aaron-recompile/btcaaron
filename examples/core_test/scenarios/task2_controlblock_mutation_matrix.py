#!/usr/bin/env python3
"""
Task 2: control-block mutation matrix (regtest).

Goal:
- demonstrate script-path tx construction with btcaaron
- inject control-block failures at raw tx witness level
- locate errors via deterministic policy reject categories
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "btcaaron" not in sys.modules:
    # Avoid importing btcaaron/__init__.py (optional dependency side effects).
    pkg = types.ModuleType("btcaaron")
    pkg.__path__ = [str(ROOT / "btcaaron")]
    sys.modules["btcaaron"] = pkg


def load_btcaaron_symbols():
    try:
        key_cls = importlib.import_module("btcaaron.key").Key
        tap_tree_cls = importlib.import_module("btcaaron.tree.builder").TapTree
        return key_cls, tap_tree_cls
    except Exception as e:
        raise RuntimeError(
            "Cannot import btcaaron Taproot stack. Install btcaaron deps (including bitcoin-utils) first."
        ) from e


def configure_bitcoinutils_network(instance: str) -> str:
    if instance != "regtest":
        raise RuntimeError(
            "task2_controlblock_mutation_matrix.py is regtest-only. "
            "It uses generatetoaddress to create mature local UTXOs."
        )
    try:
        setup_fn = importlib.import_module("bitcoinutils.setup").setup
        setup_fn("regtest")
    except Exception as e:
        raise RuntimeError("Failed to configure bitcoin-utils network context.") from e
    return "regtest"


def rpc(instance: str, method: str, *params: str) -> Any:
    cmd = ["btcrun", instance, "rpc", method, *params]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"RPC failed\ncmd: {' '.join(cmd)}\nstderr: {res.stderr.strip()}\nstdout: {res.stdout.strip()}"
        )
    out = res.stdout.strip()
    try:
        return json.loads(out)
    except Exception:
        return out


def print_case(case: str, expect: str, actual: str, verdict: str, detail: str) -> None:
    print("=" * 88)
    print(f"CASE: {case}")
    print(f"EXPECT: {expect}")
    print(f"ACTUAL: {actual}")
    print(f"VERDICT: {verdict}")
    print("DETAIL:")
    print(detail)


def find_coinbase_utxo_for_address(block: Dict[str, Any], address: str) -> Dict[str, Any]:
    coinbase_tx = block["tx"][0]
    for vout in coinbase_tx["vout"]:
        spk = vout.get("scriptPubKey", {})
        if spk.get("address") == address:
            return {
                "txid": coinbase_tx["txid"],
                "vout": vout["n"],
                "value_btc": float(vout["value"]),
            }
    raise RuntimeError(f"No coinbase output found for address {address}")


def read_varint(data: bytes, idx: int) -> Tuple[int, int]:
    prefix = data[idx]
    idx += 1
    if prefix < 0xFD:
        return prefix, idx
    if prefix == 0xFD:
        return int.from_bytes(data[idx:idx + 2], "little"), idx + 2
    if prefix == 0xFE:
        return int.from_bytes(data[idx:idx + 4], "little"), idx + 4
    return int.from_bytes(data[idx:idx + 8], "little"), idx + 8


def write_varint(value: int) -> bytes:
    if value < 0xFD:
        return bytes([value])
    if value <= 0xFFFF:
        return b"\xfd" + value.to_bytes(2, "little")
    if value <= 0xFFFFFFFF:
        return b"\xfe" + value.to_bytes(4, "little")
    return b"\xff" + value.to_bytes(8, "little")


def parse_segwit_tx(raw_hex: str) -> Dict[str, Any]:
    b = bytes.fromhex(raw_hex)
    i = 0
    version = b[i:i + 4]
    i += 4

    has_witness = len(b) > 6 and b[i] == 0x00 and b[i + 1] == 0x01
    if not has_witness:
        raise ValueError("Expected segwit transaction")
    i += 2

    vin_count, i = read_varint(b, i)
    vins = []
    for _ in range(vin_count):
        txid = b[i:i + 32]
        i += 32
        vout = b[i:i + 4]
        i += 4
        script_len, i = read_varint(b, i)
        script_sig = b[i:i + script_len]
        i += script_len
        sequence = b[i:i + 4]
        i += 4
        vins.append((txid, vout, script_sig, sequence))

    vout_count, i = read_varint(b, i)
    vouts = []
    for _ in range(vout_count):
        amount = b[i:i + 8]
        i += 8
        spk_len, i = read_varint(b, i)
        spk = b[i:i + spk_len]
        i += spk_len
        vouts.append((amount, spk))

    witnesses: List[List[bytes]] = []
    for _ in range(vin_count):
        n_items, i = read_varint(b, i)
        stack = []
        for _ in range(n_items):
            item_len, i = read_varint(b, i)
            item = b[i:i + item_len]
            i += item_len
            stack.append(item)
        witnesses.append(stack)

    locktime = b[i:i + 4]
    i += 4
    if i != len(b):
        raise ValueError("Unexpected trailing bytes in transaction")

    return {
        "version": version,
        "vins": vins,
        "vouts": vouts,
        "witnesses": witnesses,
        "locktime": locktime,
    }


def serialize_segwit_tx(tx: Dict[str, Any]) -> str:
    out = bytearray()
    out += tx["version"]
    out += b"\x00\x01"  # marker+flag

    vins = tx["vins"]
    out += write_varint(len(vins))
    for txid, vout, script_sig, sequence in vins:
        out += txid
        out += vout
        out += write_varint(len(script_sig))
        out += script_sig
        out += sequence

    vouts = tx["vouts"]
    out += write_varint(len(vouts))
    for amount, spk in vouts:
        out += amount
        out += write_varint(len(spk))
        out += spk

    for stack in tx["witnesses"]:
        out += write_varint(len(stack))
        for item in stack:
            out += write_varint(len(item))
            out += item

    out += tx["locktime"]
    return out.hex()


def mutate_control_block(raw_hex: str, mutator: Callable[[bytes], bytes]) -> Tuple[str, str, str]:
    tx = parse_segwit_tx(raw_hex)
    if not tx["witnesses"] or len(tx["witnesses"][0]) < 2:
        raise RuntimeError("Cannot locate script-path witness/control block in input 0")
    stack0 = tx["witnesses"][0]
    original_cb = stack0[-1]
    mutated_cb = mutator(original_cb)
    stack0[-1] = mutated_cb
    return serialize_segwit_tx(tx), original_cb.hex(), mutated_cb.hex()


def cb_flip_last_byte(cb: bytes) -> bytes:
    if not cb:
        return cb
    return cb[:-1] + bytes([cb[-1] ^ 0x01])


def cb_truncate_one(cb: bytes) -> bytes:
    if len(cb) <= 1:
        return b""
    return cb[:-1]


def cb_append_zero(cb: bytes) -> bytes:
    return cb + b"\x00"


def classify_reject_reason(result: Dict[str, Any]) -> str:
    detail = (result.get("reject-details") or "") + " " + (result.get("reject-reason") or "")
    if "control block size" in detail:
        return "CONTROL_BLOCK_SIZE"
    if "Witness program hash mismatch" in detail:
        return "WITNESS_PROGRAM_MISMATCH"
    if "script-verify-flag-failed" in detail:
        return "SCRIPT_VERIFY_FAILED"
    if "non-mandatory-script-verify-flag" in detail:
        return "NON_MANDATORY_SCRIPT_VERIFY_FAILED"
    return "UNKNOWN_REJECT"


def main() -> None:
    Key, TapTree = load_btcaaron_symbols()
    instance = sys.argv[1] if len(sys.argv) > 1 else "regtest"
    btc_network = configure_bitcoinutils_network(instance)
    print(f"INSTANCE: {instance}")
    print(f"BTCAARON_NETWORK: {btc_network}")

    internal_key = Key.generate()
    leaf_key = Key.generate()
    program = TapTree(internal_key=internal_key, network=btc_network).checksig(leaf_key, label="spend").build()
    recv_key = Key.generate()
    recv_addr = recv_key._internal_pub.get_taproot_address().to_string()

    block_hashes: List[str] = rpc(instance, "generatetoaddress", "101", program.address)
    if not block_hashes:
        raise RuntimeError("generatetoaddress returned no blocks.")
    first_block = rpc(instance, "getblock", block_hashes[0], "2")
    utxo = find_coinbase_utxo_for_address(first_block, program.address)

    input_sats = int(round(utxo["value_btc"] * 100_000_000))
    send_sats = input_sats - 2_000

    tx_valid = (
        program.spend("spend")
        .from_utxo(utxo["txid"], utxo["vout"], sats=input_sats)
        .to(recv_addr, send_sats)
        .sign(leaf_key)
        .build()
    )

    matrix: List[Tuple[str, Callable[[bytes], bytes]]] = [
        ("controlblock/flip_last_byte", cb_flip_last_byte),
        ("controlblock/truncate_one", cb_truncate_one),
        ("controlblock/append_zero", cb_append_zero),
    ]

    results: List[str] = []

    baseline = rpc(instance, "testmempoolaccept", json.dumps([tx_valid.hex]))[0]
    v_baseline = "PASS" if baseline.get("allowed") else "FAIL"
    results.append(v_baseline)
    print_case(
        "controlblock/baseline_valid_scriptpath",
        "allowed=true",
        f"allowed={baseline.get('allowed')}",
        v_baseline,
        json.dumps(baseline, indent=2),
    )

    for case_name, mutator in matrix:
        mutated_hex, cb_before, cb_after = mutate_control_block(tx_valid.hex, mutator)
        res = rpc(instance, "testmempoolaccept", json.dumps([mutated_hex]))[0]
        allowed = bool(res.get("allowed"))
        category = classify_reject_reason(res)
        verdict = "PASS" if not allowed else "FAIL"
        results.append(verdict)
        detail = {
            "allowed": allowed,
            "reject-reason": res.get("reject-reason"),
            "reject-details": res.get("reject-details"),
            "reject-category": category,
            "control_block_before": cb_before,
            "control_block_after": cb_after,
        }
        print_case(
            case_name,
            "allowed=false (control block mutation should fail)",
            f"allowed={allowed}, category={category}",
            verdict,
            json.dumps(detail, indent=2),
        )

    txid = rpc(instance, "sendrawtransaction", tx_valid.hex)
    rpc(instance, "generatetoaddress", "1", program.address)
    txinfo = rpc(instance, "getrawtransaction", txid, "true")
    confirmations = int(txinfo.get("confirmations", 0))
    v_mined = "PASS" if confirmations > 0 else "FAIL"
    results.append(v_mined)
    print_case(
        "controlblock/consensus_baseline_mined",
        "confirmations>0",
        f"confirmations={confirmations}",
        v_mined,
        json.dumps({"txid": txid, "confirmations": confirmations}, indent=2),
    )

    passed = sum(1 for x in results if x == "PASS")
    print("=" * 88)
    print(f"SUMMARY: {passed}/{len(results)} PASS")


if __name__ == "__main__":
    main()
