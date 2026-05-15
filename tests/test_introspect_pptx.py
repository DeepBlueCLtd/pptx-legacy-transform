"""Tests for introspect_pptx.py (User Story 3).

After the Phase 10 reverse-spec redesign the mock generator produces a
corpus rather than a single PPTX. These tests pick the Week 1 deck as a
representative single-PPTX target.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import introspect_pptx  # noqa: E402
from tests import conftest_helpers  # noqa: E402


TMP = REPO_ROOT / "tests" / "_tmp"


class IntrospectTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        corpus = conftest_helpers.make_mock_corpus(TMP / "introspect_mock")
        cls.pptx = conftest_helpers.first_pptx(corpus)
        cls.report_path = TMP / "introspect_report.txt"
        rc = introspect_pptx.main(["--input", str(cls.pptx), "--out", str(cls.report_path)])
        assert rc == 0
        cls.report = cls.report_path.read_text(encoding="utf-8")

    def test_summary_lists_extensions_seen_in_corpus(self) -> None:
        # The Week deck links to .glc, .docx/.png (analysis), and rarely .wav.
        self.assertIn(".glc:", self.report)
        # At least one of the analysis-sheet extensions must appear.
        self.assertTrue(".png:" in self.report or ".docx:" in self.report,
                        "Expected analysis-sheet extension in summary")
        self.assertIn("Shape-level hyperlinks:", self.report)
        self.assertIn("Text-run hyperlinks:", self.report)

    def test_per_slide_section_records_position_and_text(self) -> None:
        section_2 = self.report.split("=== Section 2: Per-slide ===", 1)[1]
        section_2 = section_2.split("=== Section 3:", 1)[0]
        self.assertIn("name=", section_2)
        self.assertIn("type=", section_2)
        self.assertIn("pos=(", section_2)
        self.assertIn("hyperlink=", section_2)

    def test_hyperlink_targets_section_groups_by_extension(self) -> None:
        section_3 = self.report.split("=== Section 3: Hyperlink targets ===", 1)[1]
        self.assertIn("-- .glc --", section_3)
        # At least one of the two analysis-sheet extensions must be present.
        self.assertTrue("-- .png --" in section_3 or "-- .docx --" in section_3)

    def test_slides_filter_restricts_per_slide_section(self) -> None:
        path = TMP / "introspect_filtered.txt"
        rc = introspect_pptx.main([
            "--input", str(self.pptx),
            "--out", str(path),
            "--slides", "1",
        ])
        self.assertEqual(rc, 0)
        section_2 = path.read_text(encoding="utf-8").split(
            "=== Section 2: Per-slide ===", 1)[1].split("=== Section 3:", 1)[0]
        self.assertIn("Slide 1", section_2)
        # If the deck has more than one slide, slide 2 should be filtered out.
        self.assertNotIn("Slide 2", section_2)

    def test_unexpected_shape_count_is_flagged(self) -> None:
        from pptx import Presentation
        from unittest.mock import patch
        all_records = []
        prs = Presentation(self.pptx)
        for i, slide in enumerate(prs.slides, start=1):
            all_records.extend(introspect_pptx.collect_shape_records(slide, slide_number=i))
        with patch.object(introspect_pptx, "EXPECTED_SHAPES_PER_CONTENT_SLIDE", 999), \
             patch.object(introspect_pptx, "SHAPE_DEVIATION_TOLERANCE", 0):
            text = introspect_pptx.render_summary(self.pptx.name, len(list(prs.slides)), all_records)
        self.assertIn("Slides flagged", text)
        self.assertNotIn("Slides flagged (deviating shape count): none", text)


if __name__ == "__main__":
    unittest.main()
