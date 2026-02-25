#!/usr/bin/env python3
"""
Task 4: policy vs consensus split matrix (regtest).

Demonstrates a concrete split:
- strict policy profile rejects a high-fee transaction
- consensus-valid transaction is still mineable when policy guard is relaxed
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "btcaaron" not in sys.modules:
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
            "task4_policy_consensus_split_matrix.py is regtest-only. "
            "It relies on local mining for deterministic checks."
        )
    setup_fn = importlib.import_module("bitcoinutils.setup").setup
    setup_fn("regtest")
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


def rpc_allow_error(instance: str, method: str, *params: str) -> Dict[str, Any]:
    cmd = ["btcrun", instance, "rpc", method, *params]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        out = res.stdout.strip()
        try:
            parsed = json.loads(out)
        except Exception:
            parsed = out
        return {"ok": True, "result": parsed, "stderr": res.stderr.strip(), "stdout": out}
    return {"ok": False, "result": None, "stderr": res.stderr.strip(), "stdout": res.stdout.strip()}


def print_case(case: str, expect: str, actual: str, verdict: str, detail: str) -> None:
    print("=" * 88)
    print(f"CASE: {case}")
    print(f"EXPECT: {expect}")
    print(f"ACTUAL: {actual}")
    print(f"VERDICT: {verdict}")
    print("DETAIL:")
    print(detail)


def find_coinbase_utxos(block: Dict[str, Any], address: str) -> List[Dict[str, Any]]:
    coinbase_tx = block["tx"][0]
    out: List[Dict[str, Any]] = []
    for vout in coinbase_tx["vout"]:
        spk = vout.get("scriptPubKey", {})
        if spk.get("address") == address:
            out.append(
                {
                    "txid": coinbase_tx["txid"],
                    "vout": vout["n"],
                    "value_btc": float(vout["value"]),
                }
            )
    return out


def main() -> None:
    Key, TapTree = load_btcaaron_symbols()
    instance = sys.argv[1] if len(sys.argv) > 1 else "regtest"
    btc_network = configure_bitcoinutils_network(instance)
    print(f"INSTANCE: {instance}")
    print(f"BTCAARON_NETWORK: {btc_network}")

    spend_key = Key.generate()
    recv_key = Key.generate()
    program = TapTree(internal_key=spend_key, network=btc_network).build()
    recv_addr = recv_key._internal_pub.get_taproot_address().to_string()

    block_hashes: List[str] = rpc(instance, "generatetoaddress", "102", program.address)
    if len(block_hashes) < 2:
        raise RuntimeError("Need at least 2 freshly mined blocks for this matrix.")

    spend_utxos: List[Dict[str, Any]] = []
    for h in block_hashes[:2]:
        blk = rpc(instance, "getblock", h, "2")
        spend_utxos.extend(find_coinbase_utxos(blk, program.address))
    if len(spend_utxos) < 2:
        raise RuntimeError("Cannot collect 2 coinbase UTXOs for spending.")

    utxo_normal = spend_utxos[0]
    utxo_highfee = spend_utxos[1]

    in_normal = int(round(utxo_normal["value_btc"] * 100_000_000))
    in_highfee = int(round(utxo_highfee["value_btc"] * 100_000_000))

    tx_normal = (
        program.keypath()
        .from_utxo(utxo_normal["txid"], utxo_normal["vout"], sats=in_normal)
        .to(recv_addr, in_normal - 2_000)
        .sign(spend_key)
        .build()
    )

    # Deliberately high fee to trigger strict policy profiles.
    high_fee_sats = 50_000_000
    tx_highfee = (
        program.keypath()
        .from_utxo(utxo_highfee["txid"], utxo_highfee["vout"], sats=in_highfee)
        .to(recv_addr, in_highfee - high_fee_sats)
        .sign(spend_key)
        .build()
    )

    verdicts: List[str] = []

    normal_policy = rpc(instance, "testmempoolaccept", json.dumps([tx_normal.hex]))[0]
    v_normal = "PASS" if normal_policy.get("allowed") else "FAIL"
    verdicts.append(v_normal)
    print_case(
        "policy_consensus/baseline_normal_fee_policy",
        "allowed=true",
        f"allowed={normal_policy.get('allowed')}",
        v_normal,
        json.dumps(normal_policy, indent=2),
    )

    strict_maxfeerate = "0.00001000"
    highfee_strict = rpc(
        instance,
        "testmempoolaccept",
        json.dumps([tx_highfee.hex]),
        strict_maxfeerate,
    )[0]
    allowed_strict = bool(highfee_strict.get("allowed"))
    reject_reason = (highfee_strict.get("reject-reason") or "") + " " + (highfee_strict.get("reject-details") or "")
    hit_maxfee = "max-fee-exceeded" in reject_reason
    v_strict = "PASS" if (not allowed_strict and hit_maxfee) else "FAIL"
    verdicts.append(v_strict)
    print_case(
        "policy_consensus/high_fee_strict_policy_reject",
        "allowed=false and reason contains max-fee-exceeded",
        f"allowed={allowed_strict}",
        v_strict,
        json.dumps(
            {
                "strict_maxfeerate_btc_per_kvb": strict_maxfeerate,
                "result": highfee_strict,
            },
            indent=2,
        ),
    )

    send_default = rpc_allow_error(instance, "sendrawtransaction", tx_highfee.hex)
    err_text = (send_default["stderr"] + " " + send_default["stdout"]).lower()
    default_rejected = (not send_default["ok"]) and (
        ("max-fee-exceeded" in err_text) or ("fee exceeds maximum configured by user" in err_text)
    )
    v_send_default = "PASS" if default_rejected else "FAIL"
    verdicts.append(v_send_default)
    print_case(
        "policy_consensus/high_fee_default_send_reject",
        "sendrawtransaction default rejects max-fee-exceeded",
        f"ok={send_default['ok']}",
        v_send_default,
        json.dumps(send_default, indent=2),
    )

    send_relaxed = rpc(instance, "sendrawtransaction", tx_highfee.hex, "0")
    rpc(instance, "generatetoaddress", "1", program.address)
    txinfo = rpc(instance, "getrawtransaction", send_relaxed, "true")
    confirmations = int(txinfo.get("confirmations", 0))
    v_consensus = "PASS" if confirmations > 0 else "FAIL"
    verdicts.append(v_consensus)
    print_case(
        "policy_consensus/high_fee_relaxed_policy_mined",
        "confirmations>0",
        f"confirmations={confirmations}",
        v_consensus,
        json.dumps(
            {
                "txid": send_relaxed,
                "confirmations": confirmations,
                "note": "Consensus-valid tx mined after relaxing local maxfeerate policy guard.",
            },
            indent=2,
        ),
    )

    passed = sum(1 for v in verdicts if v == "PASS")
    print("=" * 88)
    print(f"SUMMARY: {passed}/{len(verdicts)} PASS")


if __name__ == "__main__":
    main()

