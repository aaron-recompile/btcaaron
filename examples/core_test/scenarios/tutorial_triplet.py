#!/usr/bin/env python3
"""
Task 1: tutorial triplet (valid / invalid / nonstandard-candidate).

This is a teaching-oriented script built on outer_experiment_framework.
"""

from __future__ import annotations

import sys
from pathlib import Path

CORE_TEST_DIR = Path(__file__).resolve().parents[1]
FRAMEWORK_DIR = CORE_TEST_DIR / "framework"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

from outer_experiment_framework import TaprootExperiment, RpcRunner, gen_three_pubkeys


def desc_valid(ctx):
    # Valid control: plain miniscript inside tr().
    return f"tr({ctx['k1']},and_v(v:pk({ctx['k2']}),older(12960)))"


def desc_invalid(ctx):
    # Invalid control: known parser failure shape with nested pk(musig(...)).
    k1, k2, k3 = ctx["k1"], ctx["k2"], ctx["k3"]
    return (
        f"tr(musig({k1},{k2},{k3}),"
        f"{{and_v(v:pk(musig({k1},{k2})),older(12960)),"
        f"{{and_v(v:pk(musig({k1},{k3})),older(12960)),"
        f"and_v(v:pk(musig({k2},{k3})),older(12960))}}}})"
    )


def desc_nonstandard_candidate(ctx):
    # Descriptor parses successfully; policy/nonstandard verification is deferred
    # to task 4 where we execute mempool/block acceptance checks.
    return f"tr({ctx['k1']},and_v(v:pk({ctx['k2']}),older(1)))"


def main() -> None:
    instance = sys.argv[1] if len(sys.argv) > 1 else "testnet3"
    ctx = gen_three_pubkeys()

    exp = (
        TaprootExperiment(rpc=RpcRunner(instance=instance))
        .with_context(**ctx)
        .expect_success("tutorial/valid_plain_pk_timelock", desc_valid)
        .expect_failure(
            "tutorial/invalid_nested_pk_musig",
            desc_invalid,
            expect_err_contains="Invalid musig() expression",
        )
        .expect_nonstandard_candidate(
            "tutorial/nonstandard_candidate_policy_deferred",
            desc_nonstandard_candidate,
        )
    )
    exp.run(print_report=True)


if __name__ == "__main__":
    main()
