#!/usr/bin/env python3
"""
Task 7: cross-instance consistency runner.

Runs the same descriptor cases across multiple btcrun instances and reports:
- per-instance outcomes
- per-case cross-instance consistency
- divergence clusters for quick diagnosis
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORE_TEST_DIR = Path(__file__).resolve().parents[1]
FRAMEWORK_DIR = CORE_TEST_DIR / "framework"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

from outer_experiment_framework import gen_three_pubkeys


def call_getdescriptorinfo(instance: str, desc: str) -> Tuple[bool, str]:
    cmd = ["btcrun", instance, "rpc", "getdescriptorinfo", desc]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        return True, res.stdout.strip()
    detail = (
        f"cmd: {' '.join(cmd)}\n"
        f"stderr: {res.stderr.strip()}\n"
        f"stdout: {res.stdout.strip()}"
    )
    return False, detail


def classify_result(ok: bool, detail: str) -> str:
    if ok:
        return "OK"
    low = detail.lower()
    if "cannot connect to bitcoin node" in low or "connection refused" in low:
        return "RPC_OFFLINE"
    if "invalid musig() expression" in low:
        return "ERR_INVALID_MUSIG"
    return "ERR_OTHER"


def build_cases(ctx: Dict[str, str]) -> List[Tuple[str, str]]:
    k1, k2, k3 = ctx["k1"], ctx["k2"], ctx["k3"]
    return [
        ("control/musig_keypath", f"tr(musig({k1},{k2},{k3}))"),
        ("control/plain_pk_timelock", f"tr({k1},and_v(v:pk({k2}),older(12960)))"),
        (
            "target/nested_pk_musig",
            (
                f"tr(musig({k1},{k2},{k3}),"
                f"{{and_v(v:pk(musig({k1},{k2})),older(12960)),"
                f"{{and_v(v:pk(musig({k1},{k3})),older(12960)),"
                f"and_v(v:pk(musig({k2},{k3})),older(12960))}}}})"
            ),
        ),
    ]


def print_case_report(case: str, rows: List[Dict[str, Any]]) -> None:
    print("=" * 88)
    print(f"CASE: {case}")
    for row in rows:
        print(
            f"INSTANCE: {row['instance']} | CLASS: {row['class']} | "
            f"ACTUAL: {'success' if row['ok'] else 'error'}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 7 cross-instance consistency runner")
    parser.add_argument(
        "instances",
        nargs="*",
        default=["testnet3", "regtest"],
        help="btcrun instances to compare (e.g. testnet3 regtest signet)",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="optional output path for raw result json",
    )
    args = parser.parse_args()

    ctx = gen_three_pubkeys()
    cases = build_cases(ctx)

    all_rows: List[Dict[str, Any]] = []

    for case_name, desc in cases:
        case_rows: List[Dict[str, Any]] = []
        for inst in args.instances:
            ok, detail = call_getdescriptorinfo(inst, desc)
            clazz = classify_result(ok, detail)
            row = {
                "case": case_name,
                "instance": inst,
                "ok": ok,
                "class": clazz,
                "detail": detail,
                "descriptor": desc,
            }
            case_rows.append(row)
            all_rows.append(row)
        print_case_report(case_name, case_rows)

    print("=" * 88)
    print("CROSS-INSTANCE CONSISTENCY:")

    consistent_count = 0
    for case_name, _ in cases:
        rows = [r for r in all_rows if r["case"] == case_name and r["class"] != "RPC_OFFLINE"]
        classes = sorted({r["class"] for r in rows})
        if not rows:
            verdict = "SKIP"
            actual = "all_offline"
        elif len(classes) == 1:
            verdict = "CONSISTENT"
            actual = classes[0]
            consistent_count += 1
        else:
            verdict = "DIVERGENT"
            actual = ",".join(classes)
        print(f"- {case_name}: {verdict} ({actual})")

    print("=" * 88)
    print(f"SUMMARY: {consistent_count}/{len(cases)} cases CONSISTENT (excluding offline instances)")

    print("DIVERGENCE CLUSTERS:")
    clusters: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for row in all_rows:
        clusters[(row["case"], row["class"])].append(row["instance"])
    for (case_name, clazz), instances in sorted(clusters.items()):
        print(f"- {case_name} | {clazz}: {', '.join(instances)}")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
        print(f"JSON_WRITTEN: {out_path}")


if __name__ == "__main__":
    main()

