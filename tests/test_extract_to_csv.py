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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

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
        # The number comes from the integer in the deck name, not walk order.
        pub, chapter, slug = extract_to_csv.classify_publication(
            Path("/root/Tests/Progress_Test_3.pptx"), "progress_test", allocated)
        self.assertEqual(pub, "progress-test-3")
        self.assertIsNone(chapter)
        self.assertIsNone(slug)

        pub2, chapter2, slug2 = extract_to_csv.classify_publication(
            Path("/root/Nordic Fishing Vessels/01_intro.pptx"), "progress_test", allocated)
        self.assertEqual(pub2, "main")
        self.assertEqual(chapter2, "Nordic Fishing Vessels")
        self.assertEqual(slug2, "nordic-fishing-vessels")

    def test_progress_test_number_is_name_derived_not_walk_order(self) -> None:
        """The N in progress-test-N is the deck name's integer, so a scoped
        run yields the same number as a full-corpus walk (feature: stable
        test numbering under --only)."""
        allocated: dict[str, int] = {}
        # Test 2 seen first (e.g. an --only run) still gets progress-test-2.
        pub2, _, _ = extract_to_csv.classify_publication(
            Path("/root/Instructor Progress Test 2 Grams_Updated/"
                 "Instructor Progress Test 2 Grams_Updated.pptx"),
            "progress test", allocated)
        self.assertEqual(pub2, "progress-test-2")
        pub4, _, _ = extract_to_csv.classify_publication(
            Path("/root/Instructor Progress Test 4 Grams/"
                 "Instructor Progress Test 4 Grams.pptx"),
            "progress test", allocated)
        self.assertEqual(pub4, "progress-test-4")

    def test_test_number_from_name_falls_back_when_ambiguous(self) -> None:
        """No integer, or more than one, returns None so the caller can fall
        back to encounter-order allocation."""
        self.assertEqual(extract_to_csv.test_number_from_name("Progress Test 7 Grams"), 7)
        self.assertEqual(extract_to_csv.test_number_from_name("Progress Test 09"), 9)
        self.assertIsNone(extract_to_csv.test_number_from_name("Progress Test Grams"))
        self.assertIsNone(extract_to_csv.test_number_from_name("Test 3 of 4"))
        # Unnumbered names fall back to stable encounter order.
        allocated: dict[str, int] = {}
        first, _, _ = extract_to_csv.classify_publication(
            Path("/root/x/Progress Test Alpha.pptx"), "progress test", allocated)
        second, _, _ = extract_to_csv.classify_publication(
            Path("/root/y/Progress Test Beta.pptx"), "progress test", allocated)
        self.assertEqual((first, second), ("progress-test-1", "progress-test-2"))

    def test_joining_assessment_routing(self) -> None:
        """A deck whose filename contains the joining pattern routes to its own
        joining-assessment-N publication, never to main."""
        joining_allocated: dict[str, int] = {}
        pub, chapter, slug = extract_to_csv.classify_publication(
            Path("/root/Joining/Instructor Initial Joining Assessment Grams.pptx"),
            "progress test", {},
            extract_to_csv.DEFAULT_FINAL_PATTERN, {},
            extract_to_csv.DEFAULT_JOINING_PATTERN, joining_allocated)
        self.assertEqual(pub, "joining-assessment-1")
        self.assertIsNone(chapter)
        self.assertIsNone(slug)

    def test_joining_pattern_checked_before_final_and_test(self) -> None:
        """The joining bucket wins over final/test when a deck name matches more
        than one pattern, so a deliberately-named joining deck never falls
        through to those buckets."""
        joining_allocated: dict[str, int] = {}
        pub, _, _ = extract_to_csv.classify_publication(
            Path("/root/x/Joining Final Assessment Progress Test 1.pptx"),
            "progress test", {},
            "final assessment", {},
            "joining", joining_allocated)
        self.assertEqual(pub, "joining-assessment-1")

    def test_joining_allocation_is_stable_encounter_order(self) -> None:
        """Distinct joining decks number 1, 2, … in encounter order; the same
        deck stem keeps its number."""
        joining_allocated: dict[str, int] = {}
        first, _, _ = extract_to_csv.classify_publication(
            Path("/root/a/Joining Assessment Alpha.pptx"),
            "progress test", {}, "final assessment", {}, "joining", joining_allocated)
        second, _, _ = extract_to_csv.classify_publication(
            Path("/root/b/Joining Assessment Beta.pptx"),
            "progress test", {}, "final assessment", {}, "joining", joining_allocated)
        first_again, _, _ = extract_to_csv.classify_publication(
            Path("/root/a/Joining Assessment Alpha.pptx"),
            "progress test", {}, "final assessment", {}, "joining", joining_allocated)
        self.assertEqual((first, second, first_again),
                         ("joining-assessment-1", "joining-assessment-2", "joining-assessment-1"))

    def test_joining_pattern_disabled_when_empty(self) -> None:
        """An empty joining pattern disables the bucket, so a 'joining' deck
        falls through to main (back-compat with callers that don't set it)."""
        pub, chapter, _ = extract_to_csv.classify_publication(
            Path("/root/Joining Stuff/Joining Stuff.pptx"),
            "progress test", {}, "final assessment", {}, "", None)
        self.assertEqual(pub, "main")
        self.assertEqual(chapter, "Joining Stuff")

    def test_week_chapter_number_parses_week_token(self) -> None:
        """Feature 008: a "Week N" deck title yields the bare-integer week."""
        self.assertEqual(extract_to_csv.week_chapter_number("Instructor Week 1 Grams"), "1")
        self.assertEqual(extract_to_csv.week_chapter_number("Instructor Week 4 Grams_Updated"), "4")
        self.assertEqual(extract_to_csv.week_chapter_number("Week 03"), "3")  # leading zero stripped
        self.assertEqual(extract_to_csv.week_chapter_number("Week2"), "2")  # no space
        self.assertEqual(extract_to_csv.week_chapter_number("WEEK 2 grams"), "2")  # case-insensitive

    def test_week_chapter_number_blank_for_non_week_titles(self) -> None:
        """A deck with no week token (Pub10) leaves target_chapter for the analyst."""
        self.assertEqual(extract_to_csv.week_chapter_number("Instructor Pub10_Ed22B_Updated"), "")
        self.assertEqual(extract_to_csv.week_chapter_number("Nordic Fishing Vessels"), "")
        self.assertEqual(extract_to_csv.week_chapter_number(""), "")
        self.assertEqual(extract_to_csv.week_chapter_number(None), "")


class CsvWriteReadTests(unittest.TestCase):

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)

    def test_csv_columns_have_band_pair_not_freq_end(self) -> None:
        """Issue #87: freq_end is swapped in place for bandwidth, bandcentre."""
        cols = extract_to_csv.CSV_COLUMNS
        self.assertNotIn("freq_end", cols)
        self.assertIn("bandwidth", cols)
        self.assertIn("bandcentre", cols)
        # bandwidth then bandcentre, sitting where freq_end used to (after time_end).
        self.assertEqual(cols.index("bandwidth"), cols.index("time_end") + 1)
        self.assertEqual(cols.index("bandcentre"), cols.index("bandwidth") + 1)

    def test_csv_header_written_with_band_columns(self) -> None:
        out = TMP / "band_header.csv"
        extract_to_csv.write_csv([], out)
        with out.open("r", encoding="utf-8-sig", newline="") as fh:
            header = fh.readline().strip().split(",")
        self.assertIn("bandwidth", header)
        self.assertIn("bandcentre", header)
        self.assertNotIn("freq_end", header)

    def test_csv_round_trip_invariant(self) -> None:
        out = TMP / "round_trip.csv"
        rows = [{c: "" for c in extract_to_csv.CSV_COLUMNS} for _ in range(2)]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_12_lofar1.dita",
            "glc_path": "supporting/gram12/config_1.glc",
            "time_end": "271", "bandwidth": "400", "bandcentre": "200",
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
            "time_end": "271", "bandwidth": "400", "bandcentre": "200",
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


class EvenWeekSliceTests(unittest.TestCase):
    """Feature 009: no-week ``main`` decks are sliced evenly across the four
    weeks via ``target_chapter`` (replacing the leave-blank-for-analyst path)."""

    def test_even_week_assignment_contiguous_blocks(self) -> None:
        self.assertEqual(
            extract_to_csv.even_week_assignment(12),
            ["1", "1", "1", "2", "2", "2", "3", "3", "3", "4", "4", "4"],
        )
        self.assertEqual(
            extract_to_csv.even_week_assignment(10),
            ["1", "1", "1", "2", "2", "2", "3", "3", "4", "4"],
        )
        self.assertEqual(
            extract_to_csv.even_week_assignment(7),
            ["1", "1", "2", "2", "3", "3", "4"],
        )
        self.assertEqual(extract_to_csv.even_week_assignment(2), ["1", "2"])
        self.assertEqual(extract_to_csv.even_week_assignment(1), ["1"])
        self.assertEqual(extract_to_csv.even_week_assignment(0), [])

    def test_even_week_counts_differ_by_at_most_one_and_are_ordered(self) -> None:
        for total in range(0, 41):
            labels = extract_to_csv.even_week_assignment(total)
            self.assertEqual(len(labels), total)
            counts = [labels.count(str(w)) for w in range(1, 5)]
            self.assertLessEqual(max(counts) - min(counts), 1)
            # Contiguous blocks in week order (week 1 block, then week 2, …).
            self.assertEqual(labels, sorted(labels))

    def test_deck_target_chapters_routing(self) -> None:
        # No-week main deck → even slice.
        self.assertEqual(
            extract_to_csv.deck_target_chapters("main", "Pub10_Ed22B_Updated", 10),
            ["1", "1", "1", "2", "2", "2", "3", "3", "4", "4"],
        )
        # Week-token main deck → all that week (feature 008 unchanged).
        self.assertEqual(
            extract_to_csv.deck_target_chapters("main", "Instructor Week 2 Grams", 3),
            ["2", "2", "2"],
        )
        # Non-main publication → no week routing.
        self.assertEqual(
            extract_to_csv.deck_target_chapters("progress-test-1", "Test 1", 3),
            ["", "", ""],
        )
        # "Legacy Pub 10" has no week token → sliced exactly like Pub10
        # (no special case), and "Pub 10"/"10" must NOT match the week token.
        self.assertEqual(
            extract_to_csv.deck_target_chapters("main", "Legacy Pub 10", 4),
            ["1", "2", "3", "4"],
        )


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
        self.assertEqual(rows[0]["bandwidth"], "400")
        self.assertEqual(rows[0]["bandcentre"], "200")
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
        self.assertEqual(wav_row["bandwidth"], "")
        self.assertEqual(wav_row["bandcentre"], "")
        self.assertEqual(wav_row["wav_treatment"], "")
        self.assertIn("GLC not found", wav_row["warnings"])

    def test_analysis_doc_redirects_to_sibling_png(self) -> None:
        # Feature 007 (T009): a .doc/.docx analysis hyperlink with a rendered
        # sibling .png present -> the analysis row points at the .png inline,
        # target_ext is .png, and no warning is recorded.
        (self.tmp / "analysis_sheet.doc").write_bytes(b"placeholder doc")
        png = self.tmp / "analysis_sheet.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        gram = _gram(png="analysis_sheet.doc")
        rows = extract_to_csv.gram_to_rows(
            gram, publication="main", chapter="Arctic Survey",
            chapter_slug="arctic-survey",
            content_root=self.tmp, source_dir=self.tmp,
        )
        analysis = rows[-1]
        self.assertEqual(analysis["topic_type"], "analysis")
        self.assertTrue(analysis["png_path"].endswith(".png"))
        self.assertEqual(analysis["target_ext"], ".png")
        self.assertEqual(analysis["warnings"], "")
        self.assertNotEqual(analysis["file_size"], "")

    def test_analysis_docx_redirects_to_sibling_png(self) -> None:
        # As above but a .docx hyperlink (FR-004 covers both Word forms).
        (self.tmp / "analysis_sheet.docx").write_bytes(b"placeholder docx")
        png = self.tmp / "analysis_sheet.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        gram = _gram(png="analysis_sheet.docx")
        rows = extract_to_csv.gram_to_rows(
            gram, publication="main", chapter="Arctic Survey",
            chapter_slug="arctic-survey",
            content_root=self.tmp, source_dir=self.tmp,
        )
        analysis = rows[-1]
        self.assertTrue(analysis["png_path"].endswith(".png"))
        self.assertEqual(analysis["target_ext"], ".png")
        self.assertEqual(analysis["warnings"], "")

    def test_analysis_doc_without_png_records_warning(self) -> None:
        # Feature 007 (T017): a .doc analysis hyperlink whose sibling .png is
        # absent -> png_path is still the intended .png (so the generator
        # dangles an <image>, not a Word <xref>) and the row carries the
        # "analysis image not rendered" warning (FR-009/FR-010).
        (self.tmp / "analysis_sheet.doc").write_bytes(b"placeholder doc")
        gram = _gram(png="analysis_sheet.doc")
        rows = extract_to_csv.gram_to_rows(
            gram, publication="main", chapter="Arctic Survey",
            chapter_slug="arctic-survey",
            content_root=self.tmp, source_dir=self.tmp,
        )
        analysis = rows[-1]
        self.assertTrue(analysis["png_path"].endswith(".png"),
                        "png_path keeps the intended .png href even when absent")
        self.assertEqual(analysis["target_ext"], ".png")
        self.assertIn("analysis image not rendered", analysis["warnings"])
        self.assertEqual(analysis["file_size"], "")


# Issue #92: every GLC-backed gram (image or live-render .wav) needs its time +
# frequency view fields for GramFrame. These GLCs carry none of the three.
def _glc_missing_view_fields(inner_asset: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<GAPS_Lite_configuration>
  <data_source>
    <filename>W:\\AAAC\\Nordik\\{inner_asset}</filename>
    <bitmap_crop_values>
      <top_crop>1</top_crop>
    </bitmap_crop_values>
  </data_source>
  <settings>
    <lofar>
    </lofar>
  </settings>
</GAPS_Lite_configuration>
"""


class GlcViewFieldTests(unittest.TestCase):
    """Every GLC-backed gram (image or .wav) must carry the three view fields;
    extract identifies a blank rather than deferring to dedupe (#92)."""

    def setUp(self) -> None:
        self.tmp = TMP / "glc_view"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _rows(self, inner_asset: str, relaxed: bool) -> list[dict]:
        glc = self.tmp / "supporting/gram12/config_1.glc"
        glc.parent.mkdir(parents=True, exist_ok=True)
        glc.write_text(_glc_missing_view_fields(inner_asset), encoding="utf-8")
        gram = _gram(links=[("LOFAR 1", "supporting/gram12/config_1.glc")])
        return extract_to_csv.gram_to_rows(
            gram, publication="main", chapter="Arctic Survey",
            chapter_slug="arctic-survey",
            content_root=self.tmp, source_dir=self.tmp, relaxed=relaxed,
        )

    def test_strict_leaves_blanks_and_warns_per_field(self) -> None:
        for inner, ext in (("audio_clip.wav", ".wav"), ("spectro.png", ".png")):
            with self.subTest(inner=inner):
                row = self._rows(inner, relaxed=False)[0]
                self.assertEqual(row["target_ext"], ext)
                for field_name in extract_to_csv.GLC_VIEW_FIELDS:
                    self.assertEqual(row[field_name], "")
                    self.assertIn(
                        f"gram missing {field_name} — GramFrame cannot render",
                        row["warnings"])

    def test_relaxed_defaults_each_field_and_notes_it(self) -> None:
        for inner in ("audio_clip.wav", "spectro.png"):
            with self.subTest(inner=inner):
                row = self._rows(inner, relaxed=True)[0]
                for field_name in extract_to_csv.GLC_VIEW_FIELDS:
                    self.assertEqual(
                        row[field_name], extract_to_csv.RELAXED_DEFAULT)
                    self.assertIn(
                        f"gram missing {field_name} — defaulted to "
                        f"{extract_to_csv.RELAXED_DEFAULT} (--relaxed)",
                        row["warnings"])

    def test_glc_view_problems_flags_each_missing_field(self) -> None:
        for inner in ("audio_clip.wav", "spectro.png"):
            with self.subTest(inner=inner):
                problems = extract_to_csv.glc_view_problems(
                    self._rows(inner, relaxed=False))
                self.assertEqual(
                    sorted(field for _, field in problems),
                    sorted(extract_to_csv.GLC_VIEW_FIELDS))
                # Relaxed run fills the blanks, so nothing is flagged.
                self.assertEqual(
                    extract_to_csv.glc_view_problems(
                        self._rows(inner, relaxed=True)), [])

    def test_analysis_row_is_never_flagged(self) -> None:
        # An analysis sheet (.png, but topic_type "analysis") legitimately
        # carries no view fields — only GLC gram rows need them.
        analysis_rows = [{"topic_type": "analysis", "target_ext": ".png",
                          "gram_id": "5", "time_end": "", "bandwidth": "",
                          "bandcentre": ""}]
        self.assertEqual(extract_to_csv.glc_view_problems(analysis_rows), [])

    def test_dangling_glc_row_is_never_flagged(self) -> None:
        # A GLC row with no resolved asset (target_ext "") dangles per the
        # missing-asset rule; it is exempt from the view-field requirement.
        dangling = [{"topic_type": "glc", "target_ext": "", "gram_id": "5",
                     "time_end": "", "bandwidth": "", "bandcentre": ""}]
        self.assertEqual(extract_to_csv.glc_view_problems(dangling), [])


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
        # populated time_end/bandwidth/bandcentre via the parser.
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

    def test_exclude_tests_emits_only_main(self) -> None:
        # --exclude-tests walks the whole corpus but drops the progress-test
        # and final-assessment decks, leaving only the main publication so the
        # main document can be built without carving the tests out of source\.
        out_csv = TMP / "extract_exclude_tests.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.corpus),
            "--out", str(out_csv),
            "--exclude-tests",
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows, "Expected main rows from the corpus")
        pubs = {r["publication"] for r in rows}
        self.assertEqual(pubs, {"main"}, f"non-main publications leaked: {pubs}")


class OnlyChapterScopingTests(unittest.TestCase):
    """``--only <subdir>`` keeps ``--input-root`` at the corpus root and
    filters the walk to one chapter folder. Important: the CSV's path
    schema must stay corpus-root-relative (i.e. every relpath begins with
    the scoped chapter folder name), so dedupe/generate keep using the
    same hardcoded ``--image-root`` and "just work" without re-pointing.
    """

    @classmethod
    def setUpClass(cls) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        cls.corpus = conftest_helpers.make_mock_corpus(TMP / "extract_only_corpus")

    def _read(self, csv_path: Path) -> list[dict]:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_only_scopes_walk_and_keeps_corpus_root_relative_paths(self) -> None:
        out_csv = TMP / "extract_only_week1.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.corpus),
            "--out", str(out_csv),
            "--only", "Instructor Week 1 Grams",
        ])
        self.assertEqual(rc, 0)
        rows = self._read(out_csv)
        self.assertGreater(len(rows), 0, "expected non-empty CSV for scoped chapter")
        for r in rows:
            for col in ("glc_path", "png_path"):
                value = r.get(col, "")
                if not value:
                    continue
                self.assertTrue(
                    value.startswith("Instructor Week 1 Grams/"),
                    f"{col}={value!r} should start with the chapter folder so "
                    "dedupe/generate can resolve it from --image-root=<corpus>",
                )
                self.assertNotIn(
                    "Instructor Week 2 Grams", value,
                    f"--only must not leak rows from outside the scoped folder ({col}={value!r})",
                )

    def test_only_case_insensitive_match(self) -> None:
        out_csv = TMP / "extract_only_case.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.corpus),
            "--out", str(out_csv),
            "--only", "instructor week 1 grams",
        ])
        self.assertEqual(rc, 0)
        rows = self._read(out_csv)
        self.assertGreater(len(rows), 0)

    def test_only_zero_match_fails_loudly(self) -> None:
        out_csv = TMP / "extract_only_miss.csv"
        with self.assertLogs(extract_to_csv.LOGGER, level="WARNING") as cm:
            rc = extract_to_csv.main([
                "--input-root", str(self.corpus),
                "--out", str(out_csv),
                "--only", "No Such Chapter",
            ])
        self.assertEqual(rc, 1, "zero-match must fail-fast, not write an empty CSV")
        self.assertFalse(out_csv.exists(), "no CSV should be written on zero-match")
        joined = "\n".join(cm.output)
        self.assertIn("No Such Chapter", joined)
        self.assertIn("matched no PPTXs", joined)

    def test_stale_output_removed_when_run_aborts(self) -> None:
        """A pre-existing CSV is wiped at the start, so a zero-match (or any
        failing) run can't leave a previous document's extract.csv behind for
        the downstream dedupe/generate steps to silently consume."""
        out_csv = TMP / "extract_stale.csv"
        out_csv.write_text("STALE,FROM,A,DIFFERENT,DOCUMENT\r\n", encoding="utf-8-sig")
        rc = extract_to_csv.main([
            "--input-root", str(self.corpus),
            "--out", str(out_csv),
            "--only", "No Such Chapter",
        ])
        self.assertEqual(rc, 1)
        self.assertFalse(out_csv.exists(),
                         "stale output must be removed even when the run aborts")


class GlcViewFieldMainTests(unittest.TestCase):
    """End-to-end: a corpus whose GLC grams lack their view fields makes extract
    fail-fast (#92) — but --relaxed substitutes the default and completes. The
    GLCs keep their original (image) inner asset, exercising the broadened
    image-GLC requirement, not just .wav."""

    @classmethod
    def setUpClass(cls) -> None:
        import xml.etree.ElementTree as ET

        TMP.mkdir(parents=True, exist_ok=True)
        corpus = conftest_helpers.make_mock_corpus(TMP / "extract_glcview_corpus")
        cls.week1_dir = corpus / "Instructor Week 1 Grams"
        # Strip the time + band view fields from every referenced GLC (keeping
        # its original image inner asset) so each GLC gram row triggers.
        for glc_path in cls.week1_dir.rglob("*.glc"):
            tree = ET.parse(glc_path)
            root = tree.getroot()
            crops = root.find("data_source/bitmap_crop_values")
            bottom = crops.find("bottom_crop")
            if bottom is not None:
                crops.remove(bottom)
            lofar = root.find("settings/lofar")
            for tag in ("bandwidth", "bandcentre"):
                el = lofar.find(tag)
                if el is not None:
                    lofar.remove(el)
            tree.write(glc_path, encoding="utf-8", xml_declaration=True)

    def test_strict_run_fails_but_writes_csv_with_warning(self) -> None:
        out_csv = TMP / "extract_glcview_strict.csv"
        with self.assertLogs(extract_to_csv.LOGGER, level="ERROR") as cm:
            rc = extract_to_csv.main([
                "--input-root", str(self.week1_dir),
                "--out", str(out_csv),
            ])
        self.assertEqual(rc, 1)
        self.assertIn("GramFrame", "\n".join(cm.output))
        # The CSV is still written so its warnings column is inspectable.
        self.assertTrue(out_csv.exists())
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        glc_rows = [r for r in rows if r["topic_type"] == "glc"
                    and r["target_ext"]]
        self.assertTrue(glc_rows)
        self.assertTrue(all(r["time_end"] == "" for r in glc_rows))
        self.assertTrue(any("GramFrame cannot render" in r["warnings"]
                            for r in glc_rows))

    def test_relaxed_run_defaults_fields_and_succeeds(self) -> None:
        out_csv = TMP / "extract_glcview_relaxed.csv"
        rc = extract_to_csv.main([
            "--input-root", str(self.week1_dir),
            "--out", str(out_csv),
            "--relaxed",
        ])
        self.assertEqual(rc, 0)
        with out_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        glc_rows = [r for r in rows if r["topic_type"] == "glc"
                    and r["target_ext"]]
        self.assertTrue(glc_rows)
        for r in glc_rows:
            for field_name in extract_to_csv.GLC_VIEW_FIELDS:
                self.assertEqual(r[field_name], extract_to_csv.RELAXED_DEFAULT)


if __name__ == "__main__":
    unittest.main()
