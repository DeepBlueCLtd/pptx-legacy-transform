"""Tests for extract_to_csv.py (User Story 2 + Phase 10 grouping).

Post Phase 10, ``extract_grams_from_slide`` implements the reverse-spec §4
grouping rule (T104) — so these tests exercise the real end-to-end
extraction against the mock corpus, in addition to the pre-existing
classification / CSV / row-construction coverage.
"""

from __future__ import annotations

import csv
import shutil
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import extract_to_csv  # noqa: E402
import mock_pptx  # noqa: E402
from tests import conftest_helpers  # noqa: E402


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

    def test_wav_targeted_link_is_treated_as_unresolvable_glc(self) -> None:
        # Backlog 007: the audited corpus has no Lofar text run targeting
        # anything other than a .glc — every Lofar link points to a .glc.
        # The shape-grouping filter in extract_grams_from_slide drops
        # non-.glc candidates with a warning, so gram_to_rows never sees
        # one in normal operation. If it does (defensive path), the row
        # is produced as an unresolvable-GLC row — empty measurements,
        # no png_path — which downstream generate_dita skips with
        # "png_path missing" and records in skipped.txt. No row that
        # would emit broken <image> output (the failure mode that
        # motivated the rewrite).
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
        self.assertEqual(wav_row["png_path"], "",
                         "no asset is extracted from a .wav link target")
        self.assertEqual(wav_row["time_end"], "")
        self.assertEqual(wav_row["freq_end"], "")
        self.assertEqual(wav_row["wav_treatment"], "")
        self.assertIn("GLC not found", wav_row["warnings"])


class GroupingAgainstMockCorpusTests(unittest.TestCase):
    """T105 — exercise the real grouping logic against a small mock corpus.

    Uses the Week 1 deck (a fast, single-publication slice of the corpus)
    so this test stays well under the FR-017 one-minute budget.
    """

    @classmethod
    def setUpClass(cls) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        cls.corpus = conftest_helpers.make_mock_corpus(TMP / "extract_corpus")
        cls.week1_dir = cls.corpus / "Instructor Week 1 Grams"

    def test_grouping_emits_one_analysis_row_per_gram(self) -> None:
        out_csv = TMP / "extract_corpus_week1.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.week1_dir),
            "--out", str(out_csv),
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        analysis_rows = [r for r in rows if r["topic_type"] == "analysis"]
        gram_ids = {r["gram_id"] for r in rows}
        self.assertEqual(len(analysis_rows), len(gram_ids),
                         "Expected exactly one analysis row per gram")

    def test_gram_id_is_normalized_integer_form(self) -> None:
        """Per csv-schema.md the canonical ``gram_id`` cell is a plain
        integer string so authors can renumber by typing a bare number
        when refactoring content between chapters."""
        out_csv = TMP / "extract_corpus_gram_id.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.week1_dir),
            "--out", str(out_csv),
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows)
        for row in rows:
            self.assertRegex(row["gram_id"], r"^[1-9]\d*$",
                             f"gram_id not in canonical integer form: {row['gram_id']!r}")

    def test_descriptor_split_populates_vessel_name(self) -> None:
        out_csv = TMP / "extract_corpus_vessel.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.week1_dir),
            "--out", str(out_csv),
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        # Every gram has a non-empty descriptor after the colon, so every row
        # should carry the instructor-visible detail in vessel_name.
        with_detail = [r for r in rows if r["vessel_name"].strip()]
        self.assertGreater(len(with_detail), 0)

    def test_glc_resolution_succeeds_against_mock_corpus(self) -> None:
        out_csv = TMP / "extract_corpus_glc.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.week1_dir),
            "--out", str(out_csv),
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        glc_rows = [r for r in rows
                    if r["topic_type"] == "glc" and r["link_href"].lower().endswith(".glc")]
        self.assertGreater(len(glc_rows), 0)
        # Every .glc-link row should have produced a resolved glc_path and
        # populated time_end/freq_end via the parser.
        unresolved = [r for r in glc_rows if not r["glc_path"]]
        self.assertEqual(len(unresolved), 0,
                         f"Unresolved GLC links: {[r['link_href'] for r in unresolved][:5]}")

    def test_framing_slides_produce_no_csv_rows(self) -> None:
        # The mock PPTX brackets content with a welcome and an exit slide.
        # Neither should contribute rows; gram_id values must never carry
        # "Welcome" / "End of" text leaking from those slides.
        out_csv = TMP / "extract_corpus_framing.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.week1_dir),
            "--out", str(out_csv),
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows, "Expected gram rows from the Week 1 deck")
        for row in rows:
            self.assertFalse(row["gram_id"].startswith("Welcome"),
                             f"framing slide leaked into rows: {row}")
            self.assertFalse(row["gram_id"].startswith("End of"),
                             f"framing slide leaked into rows: {row}")
            self.assertNotIn("Welcome to", row["vessel_name"])
            self.assertNotIn("End of", row["vessel_name"])

    def test_progress_test_routing_with_default_pattern(self) -> None:
        # The default test pattern ("progress test", case-insensitive) should
        # route the Progress Test 1 PPTX to publication=progress-test-N.
        test1_dir = self.corpus / "Instructor Progress Test 1 Grams"
        out_csv = TMP / "extract_corpus_test1.csv"
        rc = extract_to_csv.main([
            "--input-root", str(test1_dir),
            "--out", str(out_csv),
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        pubs = {r["publication"] for r in rows}
        self.assertEqual(pubs, {"progress-test-1"}, f"unexpected publications: {pubs}")


if __name__ == "__main__":
    unittest.main()
