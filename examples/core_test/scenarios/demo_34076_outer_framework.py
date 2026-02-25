#!/usr/bin/env python3
"""
Demo for outer_experiment_framework using #34076-style descriptor cases.

Run:
  python3 examples/core_test/scenarios/demo_34076_outer_framework.py testnet3
"""

from __future__ import annotations

import sys
from pathlib import Path

CORE_TEST_DIR = Path(__file__).resolve().parents[1]
FRAMEWORK_DIR = CORE_TEST_DIR / "framework"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

from outer_experiment_framework import TaprootExperiment, RpcRunner, gen_three_pubkeys


def desc_musig_keypath(ctx):
    return f"tr(musig({ctx['k1']},{ctx['k2']},{ctx['k3']}))"


def desc_plain_miniscript(ctx):
    return f"tr({ctx['k1']},and_v(v:pk({ctx['k2']}),older(12960)))"


def desc_nested_pk_musig(ctx):
    k1, k2, k3 = ctx["k1"], ctx["k2"], ctx["k3"]
    return (
        f"tr(musig({k1},{k2},{k3}),"
        f"{{and_v(v:pk(musig({k1},{k2})),older(12960)),"
        f"{{and_v(v:pk(musig({k1},{k3})),older(12960)),"
        f"and_v(v:pk(musig({k2},{k3})),older(12960))}}}})"
    )


def main() -> None:
    instance = sys.argv[1] if len(sys.argv) > 1 else "testnet3"
    ctx = gen_three_pubkeys()

    exp = (
        TaprootExperiment(rpc=RpcRunner(instance=instance))
        .with_context(**ctx)
        .expect_success("control_musig_keypath", desc_musig_keypath)
        .expect_success("control_miniscript_plain_pk", desc_plain_miniscript)
        .expect_failure(
            "target_pk_musig_nested",
            desc_nested_pk_musig,
            expect_err_contains="Invalid musig() expression",
        )
    )
    exp.run(print_report=True)


if __name__ == "__main__":
    main()
