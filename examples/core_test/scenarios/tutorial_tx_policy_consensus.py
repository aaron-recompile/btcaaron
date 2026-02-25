#!/usr/bin/env python3
"""
Task 1 extension: transaction-level tutorial (policy vs consensus path).

Demonstrates btcaaron advantage at tx-building layer:
- build Taproot keypath spend with btcaaron
- validate via btcrun RPC (policy: testmempoolaccept, consensus path: mine after sendrawtransaction)
"""

from __future__ import annotations

import json
import importlib
import subprocess
import sys
import types
from typing import Any, Dict, List

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "btcaaron" not in sys.modules:
    # Avoid importing btcaaron/__init__.py (it pulls optional deps like requests).
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


def select_btcaaron_network(instance: str) -> str:
    if instance == "regtest":
        return "regtest"
    if instance in {"testnet", "testnet3", "testnet4", "signet", "signet_boss", "signet_inquisition"}:
        return "testnet"
    return "mainnet"


def configure_bitcoinutils_network(instance: str) -> str:
    btc_network = select_btcaaron_network(instance)
    try:
        setup_fn = importlib.import_module("bitcoinutils.setup").setup
        setup_fn(btc_network)
    except Exception as e:
        raise RuntimeError(
            "Failed to configure bitcoin-utils network context. "
            "Ensure bitcoin-utils is installed and supports this network."
        ) from e
    return btc_network


def rpc(instance: str, method: str, *params: str) -> Any:
    cmd = ["btcrun", instance, "rpc", method, *params]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        stderr = res.stderr.strip()
        hint = ""
        if "Invalid address" in stderr:
            hint = (
                "\nHint: address/network mismatch. "
                "For regtest use bcrt1... addresses (not tb1...)."
            )
        raise RuntimeError(
            f"RPC failed\ncmd: {' '.join(cmd)}\nstderr: {stderr}\nstdout: {res.stdout.strip()}{hint}"
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


def main() -> None:
    Key, TapTree = load_btcaaron_symbols()
    instance = sys.argv[1] if len(sys.argv) > 1 else "regtest"
    if instance != "regtest":
        raise RuntimeError(
            "tutorial_tx_policy_consensus.py is regtest-only. "
            "It relies on generatetoaddress to create spendable UTXOs."
        )
    btc_network = configure_bitcoinutils_network(instance)
    print(f"INSTANCE: {instance}")
    print(f"BTCAARON_NETWORK: {btc_network}")

    # 1) Build a btcaaron Taproot program (keypath only) as the funding target.
    funding_key = Key.generate()
    program = TapTree(internal_key=funding_key, network=btc_network).build()

    recv_key = Key.generate()
    recv_addr = recv_key._internal_pub.get_taproot_address().to_string()

    # 2) Mine to the btcaaron-generated taproot address so we get a mature UTXO.
    block_hashes: List[str] = rpc(instance, "generatetoaddress", "101", program.address)
    if not block_hashes:
        raise RuntimeError(
            "generatetoaddress returned no blocks. "
            "This tutorial requires a mining-capable regtest instance."
        )
    first_block = rpc(instance, "getblock", block_hashes[0], "2")
    utxo = find_coinbase_utxo_for_address(first_block, program.address)

    input_sats = int(round(utxo["value_btc"] * 100_000_000))
    send_sats = input_sats - 2_000  # simple fixed fee budget for tutorial

    # 3) Build valid and invalid (wrong-key) transactions with btcaaron SpendBuilder.
    tx_valid = (
        program.keypath()
        .from_utxo(utxo["txid"], utxo["vout"], sats=input_sats)
        .to(recv_addr, send_sats)
        .sign(funding_key)
        .build()
    )
    wrong_key = Key.generate()
    tx_invalid = (
        program.keypath()
        .from_utxo(utxo["txid"], utxo["vout"], sats=input_sats)
        .to(recv_addr, send_sats)
        .sign(wrong_key)
        .build()
    )

    # 4) Policy checks (mempool admission).
    valid_policy = rpc(instance, "testmempoolaccept", f'["{tx_valid.hex}"]')[0]
    invalid_policy = rpc(instance, "testmempoolaccept", f'["{tx_invalid.hex}"]')[0]

    verdict_valid_policy = "PASS" if valid_policy.get("allowed") else "FAIL"
    print_case(
        "tx_policy/valid_keypath",
        "allowed=true",
        f"allowed={valid_policy.get('allowed')}",
        verdict_valid_policy,
        json.dumps(valid_policy, indent=2),
    )

    verdict_invalid_policy = "PASS" if not invalid_policy.get("allowed") else "FAIL"
    print_case(
        "tx_policy/invalid_wrong_key",
        "allowed=false",
        f"allowed={invalid_policy.get('allowed')}",
        verdict_invalid_policy,
        json.dumps(invalid_policy, indent=2),
    )

    # 5) Consensus path demo: broadcast valid tx, mine block, verify confirmations.
    txid = rpc(instance, "sendrawtransaction", tx_valid.hex)
    rpc(instance, "generatetoaddress", "1", program.address)
    txinfo = rpc(instance, "getrawtransaction", txid, "true")
    confirmations = int(txinfo.get("confirmations", 0))

    verdict_consensus = "PASS" if confirmations > 0 else "FAIL"
    print_case(
        "tx_consensus/valid_mined",
        "confirmations>0",
        f"confirmations={confirmations}",
        verdict_consensus,
        json.dumps({"txid": txid, "confirmations": confirmations}, indent=2),
    )

    total_pass = sum(
        1
        for v in [verdict_valid_policy, verdict_invalid_policy, verdict_consensus]
        if v == "PASS"
    )
    print("=" * 88)
    print(f"SUMMARY: {total_pass}/3 PASS")


if __name__ == "__main__":
    main()
