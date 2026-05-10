"""Tests for mock_pptx.py (User Story 4)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import mock_pptx  # noqa: E402

from pptx import Presentation
from pptx.oxml.ns import qn

TMP = REPO_ROOT / "tests" / "_tmp"


def _shape_hyperlink(shape) -> str | None:
    nv_sp_pr = shape._element.find(qn("p:nvSpPr"))
    if nv_sp_pr is None:
        return None
    nv_pr = nv_sp_pr.find(qn("p:nvPr"))
    if nv_pr is None:
        return None
    hlink = nv_pr.find(qn("a:hlinkClick"))
    if hlink is None:
        return None
    rel_id = hlink.get(qn("r:id"))
    if not rel_id:
        return None
    return shape.part.rels[rel_id].target_ref


class MockPptxTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        cls.path = TMP / "mock_test.pptx"
        rc = mock_pptx.main(["--out", str(cls.path)])
        assert rc == 0
        cls.prs = Presentation(cls.path)
        cls.content_slides = list(cls.prs.slides)[1:]

    def test_slide_count(self) -> None:
        self.assertEqual(len(list(self.prs.slides)), mock_pptx.TOTAL_SLIDE_COUNT)

    def test_each_content_slide_has_15_grams(self) -> None:
        # Each gram contributes a title rectangle + a link text box.
        for slide in self.content_slides:
            text_shapes = [s for s in slide.shapes if s.has_text_frame]
            # 15 titles + 15 link boxes.
            self.assertEqual(len(text_shapes), mock_pptx.GRAMS_PER_SLIDE * 2,
                             f"slide has {len(text_shapes)} text shapes; expected 30")

    def test_title_shapes_have_shape_level_hyperlinks(self) -> None:
        found = 0
        for slide in self.content_slides:
            for shape in slide.shapes:
                target = _shape_hyperlink(shape)
                if target and target.endswith("_analysis.png"):
                    found += 1
        self.assertEqual(found, mock_pptx.TOTAL_GRAMS,
                         f"expected {mock_pptx.TOTAL_GRAMS} shape-level analysis hyperlinks; found {found}")

    def test_link_boxes_have_text_run_hyperlinks(self) -> None:
        run_targets: list[str] = []
        for slide in self.content_slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        try:
                            target = run.hyperlink.address
                        except Exception:
                            target = None
                        if target:
                            run_targets.append(target)
        self.assertGreater(len(run_targets), 0)
        for t in run_targets:
            self.assertTrue(t.endswith(".glc") or t.endswith(".wav"),
                            f"unexpected text-run hyperlink target: {t}")

    def test_wav_grams_have_wav_link(self) -> None:
        wav_targets: list[str] = []
        for slide in self.content_slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        try:
                            target = run.hyperlink.address
                        except Exception:
                            target = None
                        if target and target.endswith(".wav"):
                            wav_targets.append(target)
        self.assertEqual(len(wav_targets), len(mock_pptx.WAV_GRAMS),
                         f"expected one .wav link per WAV gram; got {wav_targets}")


if __name__ == "__main__":
    unittest.main()
