#!/usr/bin/env python3
"""
Outer experimental framework (phase-1, no btcaaron core changes).

Task 5: lightweight failure injection (overlay style)
Task 6: reproducible output contract (CASE/EXPECT/ACTUAL/VERDICT)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import subprocess
import sys
from pathlib import Path

# Allow direct execution from examples/ without pip install -e .
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

Context = Dict[str, Any]
DescriptorBuilder = Callable[[Context], str]
OverlayValue = Any
Overlay = Dict[str, OverlayValue]


def _resolve_overlay_value(value: OverlayValue, ctx: Context) -> Any:
    if callable(value):
        return value(ctx)
    return value


def apply_overlay(base_ctx: Context, overlay: Optional[Overlay]) -> Context:
    """
    Core-inspired lightweight failure injection:
    - start from base context
    - selectively override fields
    - override values can be static or callables(ctx)->value
    """
    out = dict(base_ctx)
    if not overlay:
        return out
    for key, value in overlay.items():
        out[key] = _resolve_overlay_value(value, out)
    return out


def gen_three_pubkeys() -> Context:
    # Prefer btcaaron Key API; fallback to bitcoin-utils direct generation.
    try:
        from btcaaron.key import Key  # avoid btcaaron.__init__ heavy imports
        return {
            "k1": Key.generate().pubkey,
            "k2": Key.generate().pubkey,
            "k3": Key.generate().pubkey,
        }
    except Exception:
        pass

    try:
        from bitcoinutils.keys import PrivateKey
        return {
            "k1": PrivateKey().get_public_key().to_hex(),
            "k2": PrivateKey().get_public_key().to_hex(),
            "k3": PrivateKey().get_public_key().to_hex(),
        }
    except Exception as exc:
        raise RuntimeError(
            "Cannot generate pubkeys. Install btcaaron deps or bitcoin-utils."
        ) from exc


@dataclass
class CaseResult:
    case: str
    expect: str
    actual: str
    verdict: str
    descriptor: str
    detail: str


@dataclass
class ExperimentCase:
    name: str
    kind: str  # "success" | "failure" | "nonstandard_candidate"
    builder: DescriptorBuilder
    overlay: Optional[Overlay] = None
    expect_err_contains: Optional[str] = None


@dataclass
class RpcRunner:
    instance: str = "testnet3"

    def getdescriptorinfo(self, desc: str) -> Tuple[bool, str]:
        cmd = ["btcrun", self.instance, "rpc", "getdescriptorinfo", desc]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        detail = (
            f"cmd: {' '.join(cmd)}\n"
            f"stderr: {result.stderr.strip()}\n"
            f"stdout: {result.stdout.strip()}"
        )
        return False, detail


@dataclass
class TaprootExperiment:
    rpc: RpcRunner
    base_context: Context = field(default_factory=dict)
    cases: List[ExperimentCase] = field(default_factory=list)
    results: List[CaseResult] = field(default_factory=list)

    def with_context(self, **kwargs: Any) -> "TaprootExperiment":
        self.base_context.update(kwargs)
        return self

    def expect_success(
        self,
        name: str,
        builder: DescriptorBuilder,
        overlay: Optional[Overlay] = None,
    ) -> "TaprootExperiment":
        self.cases.append(ExperimentCase(name=name, kind="success", builder=builder, overlay=overlay))
        return self

    def expect_failure(
        self,
        name: str,
        builder: DescriptorBuilder,
        *,
        expect_err_contains: str,
        overlay: Optional[Overlay] = None,
    ) -> "TaprootExperiment":
        self.cases.append(
            ExperimentCase(
                name=name,
                kind="failure",
                builder=builder,
                overlay=overlay,
                expect_err_contains=expect_err_contains,
            )
        )
        return self

    def expect_nonstandard_candidate(
        self,
        name: str,
        builder: DescriptorBuilder,
        overlay: Optional[Overlay] = None,
    ) -> "TaprootExperiment":
        """
        Marks a case as "nonstandard candidate" when descriptor parses successfully.
        Policy/consensus split verification is handled by later tasks (e.g. task 4).
        """
        self.cases.append(
            ExperimentCase(
                name=name,
                kind="nonstandard_candidate",
                builder=builder,
                overlay=overlay,
            )
        )
        return self

    def run(self, print_report: bool = True) -> List[CaseResult]:
        self.results = []
        for case in self.cases:
            ctx = apply_overlay(self.base_context, case.overlay)
            desc = case.builder(ctx)
            ok, detail = self.rpc.getdescriptorinfo(desc)

            if case.kind == "success":
                verdict = "PASS" if ok else "FAIL"
                actual = "success" if ok else "error"
                expect = "success"
            elif case.kind == "nonstandard_candidate":
                verdict = "PASS" if ok else "FAIL"
                actual = "parsed_nonstandard_candidate" if ok else "error"
                expect = "descriptor parses (policy check deferred)"
            else:
                hit = (not ok) and (case.expect_err_contains in detail if case.expect_err_contains else True)
                verdict = "PASS" if hit else "FAIL"
                actual = "expected_error" if hit else ("success" if ok else "wrong_error")
                expect = f"error contains: {case.expect_err_contains}"

            self.results.append(
                CaseResult(
                    case=case.name,
                    expect=expect,
                    actual=actual,
                    verdict=verdict,
                    descriptor=desc,
                    detail=detail,
                )
            )

        if print_report:
            self.print_report()
        return self.results

    # Task 6: reproducible output contract
    def print_report(self) -> None:
        print(f"INSTANCE: {self.rpc.instance}")
        for r in self.results:
            print("=" * 88)
            print(f"CASE: {r.case}")
            print(f"EXPECT: {r.expect}")
            print(f"ACTUAL: {r.actual}")
            print(f"VERDICT: {r.verdict}")
            print(f"DESCRIPTOR: {r.descriptor}")
            print("DETAIL:")
            print(r.detail)
        print("=" * 88)
        passed = sum(1 for r in self.results if r.verdict == "PASS")
        print(f"SUMMARY: {passed}/{len(self.results)} PASS")

    def to_json(self) -> str:
        return json.dumps([r.__dict__ for r in self.results], indent=2, ensure_ascii=False)

