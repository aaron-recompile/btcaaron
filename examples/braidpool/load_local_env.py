"""
Load KEY=VALUE from the repository root ``.env`` into os.environ (only unset keys).

Used by ``braidpool_config`` and the demo scripts so ``CAT_DEMO_WIF`` and
``INQUISITION_*`` need not be exported in every shell.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROOT_ENV = _REPO_ROOT / ".env"


def load_dotenv_files() -> None:
    if not _ROOT_ENV.is_file():
        return
    try:
        text = _ROOT_ENV.read_text(encoding="utf-8")
    except OSError:
        return
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip().strip('"').strip("'")
        if key not in os.environ:
            os.environ[key] = val


load_dotenv_files()
