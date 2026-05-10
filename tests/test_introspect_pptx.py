"""Tests for introspect_pptx.py (User Story 3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import introspect_pptx  # noqa: E402
import mock_pptx  # noqa: E402
from tests import conftest_helpers  # noqa: E402


TMP = REPO_ROOT / "tests" / "_tmp"


class IntrospectTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        cls.pptx = conftest_helpers.make_mock_pptx(TMP / "introspect_mock")
        cls.report_path = TMP / "introspect_report.txt"
        rc = introspect_pptx.main(["--input", str(cls.pptx), "--out", str(cls.report_path)])
        assert rc == 0
        cls.report = cls.report_path.read_text(encoding="utf-8")

    def test_summary_counts_match_mock_structure(self) -> None:
        self.assertIn(f"Total slides: {mock_pptx.TOTAL_SLIDE_COUNT}", self.report)
        # Shape-level count == TOTAL_GRAMS (one per title rectangle).
        self.assertIn(f"Shape-level hyperlinks: {mock_pptx.TOTAL_GRAMS}", self.report)
        # PNG hyperlinks (analysis) come from shape-level; .glc/.wav come from runs.
        self.assertIn(".png:", self.report)
        self.assertIn(".glc:", self.report)
        self.assertIn(".wav:", self.report)

    def test_per_slide_section_records_position_and_text(self) -> None:
        section_2 = self.report.split("=== Section 2: Per-slide ===", 1)[1]
        section_2 = section_2.split("=== Section 3:", 1)[0]
        # Per-slide entries include shape index, name, type, pos and run hyperlinks.
        self.assertIn("name=", section_2)
        self.assertIn("type=", section_2)
        self.assertIn("pos=(", section_2)
        self.assertIn("hyperlink=", section_2)

    def test_hyperlink_targets_section_groups_by_extension(self) -> None:
        section_3 = self.report.split("=== Section 3: Hyperlink targets ===", 1)[1]
        self.assertIn("-- .png --", section_3)
        self.assertIn("-- .glc --", section_3)
        self.assertIn("-- .wav --", section_3)

    def test_slides_filter_restricts_per_slide_section(self) -> None:
        path = TMP / "introspect_filtered.txt"
        rc = introspect_pptx.main([
            "--input", str(self.pptx),
            "--out", str(path),
            "--slides", "2",
        ])
        self.assertEqual(rc, 0)
        section_2 = path.read_text(encoding="utf-8").split(
            "=== Section 2: Per-slide ===", 1)[1].split("=== Section 3:", 1)[0]
        self.assertIn("Slide 2", section_2)
        self.assertNotIn("Slide 3", section_2)

    def test_unexpected_shape_count_is_flagged(self) -> None:
        # The mock's content slides are by construction *not* deviating, so
        # this test asserts the negative path is reachable when the
        # expected-shape constant is wildly off.
        from collections import defaultdict
        all_records = []
        from pptx import Presentation
        prs = Presentation(self.pptx)
        for i, slide in enumerate(prs.slides, start=1):
            all_records.extend(introspect_pptx.collect_shape_records(slide, slide_number=i))
        # Patch the threshold so every slide counts as deviating.
        from unittest.mock import patch
        with patch.object(introspect_pptx, "EXPECTED_SHAPES_PER_CONTENT_SLIDE", 999), \
             patch.object(introspect_pptx, "SHAPE_DEVIATION_TOLERANCE", 0):
            text = introspect_pptx.render_summary(self.pptx.name, len(list(prs.slides)), all_records)
        self.assertIn("Slides flagged", text)
        self.assertNotIn("Slides flagged (deviating shape count): none", text)


if __name__ == "__main__":
    unittest.main()
