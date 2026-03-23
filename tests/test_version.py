"""Release metadata: package __version__ must match setup.py (single source of truth for PyPI)."""

from __future__ import annotations

import re
from pathlib import Path


def test_version_matches_setup_py() -> None:
    root = Path(__file__).resolve().parents[1]
    setup_text = (root / "setup.py").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_text)
    assert m is not None, "version= not found in setup.py"
    from btcaaron import __version__

    assert __version__ == m.group(1), (
        f"btcaaron.__version__={__version__!r} != setup.py version={m.group(1)!r}"
    )
