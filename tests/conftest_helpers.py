"""Test helpers shared between user stories.

Not a pytest ``conftest.py`` (this project uses standard-library
``unittest`` per FR-017 / R13). After the Phase 10 reverse-spec
redesign, the mock generator builds a corpus rather than a single
PPTX, so the helper returns the corpus root and exposes a small
utility for picking a representative PPTX from it.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import mock_pptx  # noqa: E402


def make_mock_corpus(tmp_path: Path) -> Path:
    """Generate the mock corpus under ``tmp_path`` and return the corpus root."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    rc = mock_pptx.main(["--out-root", str(tmp_path)])
    if rc != 0:
        raise RuntimeError(f"mock_pptx.main exited {rc}")
    return tmp_path


def first_pptx(corpus_root: Path) -> Path:
    """Return a deterministic PPTX from the corpus (Week 1) for single-deck tests."""
    candidate = corpus_root / "Instructor Week 1 Grams" / "Instructor Week 1 Grams.pptx"
    if not candidate.is_file():
        raise FileNotFoundError(
            f"Expected mock corpus PPTX not found: {candidate}. "
            "Did mock_pptx.main run successfully?"
        )
    return candidate
