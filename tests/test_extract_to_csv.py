"""Tests for extract_to_csv.py infrastructure (User Story 2).

The shape-grouping function (`extract_grams_from_slide`) is the documented
``NotImplementedError`` stub mandated by FR-015 / R1, so these tests cover
the surrounding infrastructure: argument parsing, walking, classification,
GLC resolution, row construction, and CSV writing.
"""

from __future__ import annotations

import csv
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import extract_to_csv  # noqa: E402
import mock_pptx  # noqa: E402


TMP = REPO_ROOT / "tests" / "_tmp"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _gram(gram_id: str = "Gram 12", vessel: str = "Nordik Jockey",
          links: list[tuple[str, str]] | None = None,
          png: str = "images/gram12_analysis.png") -> extract_to_csv.GramPlaceholder:
    if links is None:
        links = [("LOFAR 1", "supporting/gram12/config_1.glc")]
    return extract_to_csv.GramPlaceholder(
        gram_id=gram_id, vessel_name=vessel, png_href=png,
        glc_links=[extract_to_csv.GlcLink(display_text=t, href=h) for t, h in links],
    )


class ClassificationTests(unittest.TestCase):

    def test_progress_test_routing(self) -> None:
        allocated: dict[str, int] = {}
        pub, chapter, slug = extract_to_csv.classify_publication(
            Path("/root/Tests/Progress_Test_3.pptx"), "progress_test", allocated)
        self.assertEqual(pub, "progress-test-1")
        self.assertIsNone(chapter)
        self.assertIsNone(slug)

        pub2, chapter2, slug2 = extract_to_csv.classify_publication(
            Path("/root/Nordic Fishing Vessels/01_intro.pptx"), "progress_test", allocated)
        self.assertEqual(pub2, "main")
        self.assertEqual(chapter2, "Nordic Fishing Vessels")
        self.assertEqual(slug2, "nordic-fishing-vessels")


class CsvWriteReadTests(unittest.TestCase):

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)

    def test_csv_round_trip_invariant(self) -> None:
        out = TMP / "round_trip.csv"
        rows = [{c: "" for c in extract_to_csv.CSV_COLUMNS} for _ in range(2)]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_12_lofar1.dita",
            "glc_path": "supporting/gram12/config_1.glc",
            "time_end": "271", "freq_end": "400",
            "png_path": "images/gram12.png",
        })
        rows[1].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "analysis", "sequence": "1",
            "topic_filename": "gram_12_analysis.dita",
            "png_path": "images/gram12_analysis.png",
        })
        extract_to_csv.write_csv(rows, out)
        with out.open("r", encoding="utf-8-sig", newline="") as fh:
            read_back = list(csv.DictReader(fh))
        self.assertEqual(len(read_back), 2)
        for original, parsed in zip(rows, read_back):
            for col in extract_to_csv.CSV_COLUMNS:
                self.assertEqual(parsed[col], original[col])

    def test_csv_byte_level_round_trip(self) -> None:
        # The csv-schema contract claims read(csv) -> write(csv) is
        # byte-identical for clean rows. Verify by writing, reading back
        # via DictReader, and rewriting with the same writer settings.
        out_a = TMP / "round_trip_a.csv"
        out_b = TMP / "round_trip_b.csv"
        rows = [{c: "" for c in extract_to_csv.CSV_COLUMNS} for _ in range(3)]
        rows[0].update({
            "publication": "main", "chapter": "Nordic Fishing Vessels",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_12_lofar1.dita",
            "display_text": "LOFAR 1",
            "link_href": "supporting/gram12/config_1.glc",
            "glc_path": "supporting/gram12/config_1.glc",
            "time_end": "271", "freq_end": "400",
            "png_path": "images/gram12.png",
        })
        rows[1].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 05", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_05_lofar1.dita",
            "display_text": "Audio sample",
            "link_href": "supporting/gram05/audio_clip.wav",
            "wav_treatment": "gaps-lite",
        })
        rows[2].update({
            "publication": "progress-test-1", "chapter": "",
            "gram_id": "Gram 03", "vessel_name": "",
            "topic_type": "analysis", "sequence": "1",
            "topic_filename": "gram_03_analysis.dita",
            "png_path": "images/gram03_analysis.png",
        })
        extract_to_csv.write_csv(rows, out_a)
        with out_a.open("r", encoding="utf-8-sig", newline="") as fh:
            read_back = list(csv.DictReader(fh))
        # Rebuild with all declared columns so DictWriter behaves identically.
        rebuilt = [{c: row.get(c, "") for c in extract_to_csv.CSV_COLUMNS}
                   for row in read_back]
        extract_to_csv.write_csv(rebuilt, out_b)
        self.assertEqual(out_a.read_bytes(), out_b.read_bytes(),
                         "Read-then-write must be byte-identical "
                         "(BOM, line endings, quoting all preserved)")


class GramToRowsTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = TMP / "gram_rows"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)
        # Provide one resolvable GLC and leave another unresolvable.
        glc = self.tmp / "supporting/gram12/config_1.glc"
        glc.parent.mkdir(parents=True)
        shutil.copy(FIXTURES / "minimal.glc", glc)

    def test_missing_glc_records_warning_not_raises(self) -> None:
        gram = _gram(links=[("LOFAR 1", "supporting/gram99/config_1.glc")])
        rows = extract_to_csv.gram_to_rows(
            gram, publication="progress-test-1", chapter=None, chapter_slug=None,
            content_root=self.tmp, source_dir=self.tmp,
        )
        self.assertEqual(len(rows), 2)  # 1 glc + 1 analysis
        self.assertIn("GLC not found", rows[0]["warnings"])

    def test_resolvable_glc_populates_measurements(self) -> None:
        gram = _gram(links=[("LOFAR 1", "supporting/gram12/config_1.glc")])
        rows = extract_to_csv.gram_to_rows(
            gram, publication="main", chapter="Arctic Survey",
            chapter_slug="arctic-survey",
            content_root=self.tmp, source_dir=self.tmp,
        )
        self.assertEqual(rows[0]["time_end"], "271")
        self.assertEqual(rows[0]["freq_end"], "400")
        self.assertEqual(rows[0]["png_path"], "gram12.PNG")
        self.assertEqual(rows[0]["link_href"], "supporting/gram12/config_1.glc")

    def test_wav_link_row_shape(self) -> None:
        # FR-011: a .wav link target produces a GLC-typed row with empty
        # glc_path/time_end/freq_end, the raw URL in link_href, the visible
        # label in display_text, and the "treatment required" warning.
        gram = _gram(links=[("Audio sample", "supporting/gram12/audio_clip.wav")])
        rows = extract_to_csv.gram_to_rows(
            gram, publication="main", chapter="Arctic Survey",
            chapter_slug="arctic-survey",
            content_root=self.tmp, source_dir=self.tmp,
        )
        wav_row = rows[0]
        self.assertEqual(wav_row["topic_type"], "glc")
        self.assertEqual(wav_row["display_text"], "Audio sample")
        self.assertEqual(wav_row["link_href"],
                         "supporting/gram12/audio_clip.wav")
        self.assertEqual(wav_row["glc_path"], "")
        self.assertEqual(wav_row["time_end"], "")
        self.assertEqual(wav_row["freq_end"], "")
        self.assertEqual(wav_row["png_path"], "")
        self.assertEqual(wav_row["wav_treatment"], "")
        self.assertIn("WAV link; treatment required", wav_row["warnings"])


class StubBoundaryTests(unittest.TestCase):
    """Argparse + walk + classify + write all run; only the stub raises (FR-015)."""

    def setUp(self) -> None:
        self.input_root = TMP / "stub_boundary"
        if self.input_root.exists():
            shutil.rmtree(self.input_root)
        self.input_root.mkdir(parents=True)

    def test_argparse_and_logging_succeed_before_stub(self) -> None:
        # Generate a real mock pptx so python-pptx parses successfully and
        # we hit the shape-grouping stub. The script should exit 1 but
        # everything before the stub must run.
        pptx = self.input_root / "01.pptx"
        mock_pptx.main(["--out", str(pptx)])
        out_csv = TMP / "stub_boundary.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.input_root),
            "--out", str(out_csv),
        ])
        self.assertEqual(rc, 1, "stub must trip exit 1")
        self.assertTrue(out_csv.is_file(), "header must be written even on stub")
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            self.assertEqual(tuple(reader.fieldnames or ()), extract_to_csv.CSV_COLUMNS)


class StubExpansionTests(unittest.TestCase):
    """With the stub patched out, the rest of the pipeline runs end-to-end."""

    def setUp(self) -> None:
        self.input_root = TMP / "stub_patched"
        if self.input_root.exists():
            shutil.rmtree(self.input_root)
        self.input_root.mkdir(parents=True)

    def test_full_run_with_stub_patched(self) -> None:
        pptx = self.input_root / "01.pptx"
        mock_pptx.main(["--out", str(pptx)])
        glc_dir = self.input_root / "supporting" / "gram01"
        glc_dir.mkdir(parents=True)
        shutil.copy(FIXTURES / "minimal.glc", glc_dir / "config_1.glc")

        # Stub returns one fake gram per slide.
        def fake(slide, slide_num):
            if slide_num == 1:
                return []
            return [_gram(gram_id="Gram 01", vessel="Test",
                          links=[("LOFAR 1", "supporting/gram01/config_1.glc")],
                          png="images/gram01_analysis.png")]

        out_csv = TMP / "stub_patched.csv"
        with patch.object(extract_to_csv, "extract_grams_from_slide", fake):
            rc = extract_to_csv.main([
                "--input-root", str(self.input_root),
                "--out", str(out_csv),
            ])
        self.assertEqual(rc, 0)
        self.assertTrue(out_csv.is_file())
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertGreaterEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
