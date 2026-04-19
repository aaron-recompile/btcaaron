"""
Load KEY=VALUE pairs from a `.env` file at the btcaaron repo root into os.environ.
Only sets keys that are NOT already in the environment, so an explicit `export`
always wins.

Looked-up locations (first existing wins):
  <btcaaron-repo-root>/.env
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
        text = _ROOT_ENV.read_text()
    except OSError:
        return
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv_files()
