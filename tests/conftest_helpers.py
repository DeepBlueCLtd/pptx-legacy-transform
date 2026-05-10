"""Test helpers shared between user stories.

Not a pytest ``conftest.py`` (this project uses standard-library
``unittest`` per FR-017 / R13). The ``make_mock_pptx`` helper writes the
mock to a per-test directory under ``tests/_tmp/`` so the binary is not
committed and individual tests can rebuild it on demand.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import mock_pptx  # noqa: E402


def make_mock_pptx(tmp_path: Path) -> Path:
    """Generate the mock PPTX under ``tmp_path`` and return its path."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    out = tmp_path / "mock.pptx"
    rc = mock_pptx.main(["--out", str(out)])
    if rc != 0:
        raise RuntimeError(f"mock_pptx.main exited {rc}")
    return out
