"""
btcaaron_doctor - environment diagnostics for installation/runtime issues.

This module is intentionally top-level (not under btcaaron package) so it can
run even when btcaaron package imports fail due to missing dependencies.
"""

from __future__ import annotations

import importlib.util
import platform
import sys
from importlib import metadata


def _parse_version_tuple(v: str) -> tuple[int, int, int]:
    parts = []
    for token in v.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
        if len(parts) == 3:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _check_range(version: str, lower: str, upper: str) -> bool:
    v = _parse_version_tuple(version)
    lo = _parse_version_tuple(lower)
    hi = _parse_version_tuple(upper)
    return lo <= v < hi


def main() -> int:
    print("=== btcaaron doctor ===")
    print(f"python_executable: {sys.executable}")
    print(f"python_version: {platform.python_version()}")

    py_ok = _check_range(platform.python_version(), "3.10.0", "3.13.0")
    print(f"python_supported: {'PASS' if py_ok else 'FAIL'} (required: >=3.10,<3.13)")

    required = [
        ("requests", "2.25.0", "3.0.0"),
        ("bitcoin-utils", "0.7.3", "0.8.0"),
    ]

    dep_fail = False
    for dist_name, lo, hi in required:
        try:
            version = metadata.version(dist_name)
            in_range = _check_range(version, lo, hi)
            print(
                f"dep {dist_name}: {version} "
                f"{'PASS' if in_range else f'FAIL (need >={lo},<{hi})'}"
            )
            dep_fail = dep_fail or (not in_range)
        except metadata.PackageNotFoundError:
            print(f"dep {dist_name}: MISSING (need >={lo},<{hi})")
            dep_fail = True

    modules = ["bitcoinutils", "requests", "btcaaron"]
    for module_name in modules:
        found = importlib.util.find_spec(module_name) is not None
        print(f"module {module_name}: {'FOUND' if found else 'MISSING'}")

    if py_ok and not dep_fail:
        print("doctor_result: PASS")
        return 0

    print("doctor_result: FAIL")
    print("fix_hint:")
    print("  1) Use one interpreter consistently.")
    print("  2) Reinstall with that interpreter:")
    print("     python -m pip install -e .")
    print("  3) Re-run doctor:")
    print("     btcaaron-doctor")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
