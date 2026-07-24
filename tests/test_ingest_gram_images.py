"""Tests for ingest_gram_images.py.

Exercises the two-phase import of author-supplied gram screenshots: duration
parsing, container resolution, folder/stem matching with nearest-candidate
suggestions and trend grouping, the read-only verify guarantee, the apply-mode
GLC rewrite + crop insertion + image copy (wav deliberately left in place),
idempotency, and every warn-and-skip class. Stdlib-only.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ingest_gram_images as ingest  # noqa: E402
from extract_to_csv import parse_glc  # noqa: E402

WAV_GLC = (
    "<GAPS_Lite_configuration>\n"
    "  <data_source>\n"
    "    <filename>W:\\aaac\\{name}</filename>\n"
    "  </data_source>\n"
    "  <settings>\n"
    "    <lofar>\n"
    "      <bandwidth>400</bandwidth>\n"
    "      <bandcentre>200</bandcentre>\n"
    "    </lofar>\n"
    "  </settings>\n"
    "</GAPS_Lite_configuration>\n"
)

# A GLC that already carries a bitmap_crop_values structure while still
# referencing a wav -- the anomalous glc-already-cropped case.
WAV_GLC_CROPPED = (
    "<GAPS_Lite_configuration>\n"
    "  <data_source>\n"
    "    <filename>W:\\aaac\\{name}</filename>\n"
    "    <bitmap_crop_values>\n"
    "      <bottom_crop>99</bottom_crop>\n"
    "    </bitmap_crop_values>\n"
    "  </data_source>\n"
    "</GAPS_Lite_configuration>\n"
)


class IngestTestBase(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.incoming = self.root / "incoming"
        self.source = self.root / "source"
        self.incoming.mkdir()
        self.source.mkdir()

    # --- source tree builders ---------------------------------------------

    def source_gram(self, doc: str, gram: str,
                    container: str = None) -> Path:
        """Create source/<doc>/<container>/<gram>/ and return the gram dir."""
        container = container or (doc + " Files")
        path = self.source / doc / container / gram
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_wav_glc(self, gram: Path, glc_name: str, wav_name: str,
                      *, template: str = WAV_GLC) -> Path:
        path = gram / glc_name
        path.write_text(template.format(name=wav_name), encoding="utf-8")
        (gram / wav_name).write_bytes(b"RIFFfakeaudio")
        return path

    # --- incoming tree builders -------------------------------------------

    def incoming_image(self, doc: str, gram: str, filename: str,
                       data: bytes = b"\x89PNGdata") -> Path:
        folder = self.incoming / doc / gram
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        path.write_bytes(data)
        return path

    # --- run helpers -------------------------------------------------------

    def run_ingest(self, *, apply: bool):
        return ingest.ingest_tree(self.incoming, self.source, apply=apply)

    def kinds(self, outcomes):
        return sorted(o.kind for o in outcomes)

    def of_kind(self, outcomes, kind):
        return [o for o in outcomes if o.kind == kind]

    def snapshot(self, root: Path):
        """Map of relative path -> bytes for every file under root."""
        out = {}
        for p in sorted(root.rglob("*")):
            if p.is_file():
                out[p.relative_to(root).as_posix()] = p.read_bytes()
        return out


# ---------------------------------------------------------------------------
# Foundational: duration parsing + extension gate
# ---------------------------------------------------------------------------

class DurationParsingTests(IngestTestBase):

    def parse(self, name: str):
        return ingest.parse_image_filename(Path(name))

    def test_minutes_and_seconds(self):
        ci = self.parse("5m26s WAV 1.jpg")
        self.assertEqual(ci.seconds, 326)
        self.assertEqual(ci.stem, "WAV 1")
        self.assertEqual(ci.extension, ".jpg")
        self.assertTrue(ci.parseable)

    def test_whole_minutes(self):
        ci = self.parse("21m WAVE 3.png")
        self.assertEqual(ci.seconds, 21 * 60)
        self.assertEqual(ci.stem, "WAVE 3")

    def test_zero_minutes_applied_as_is(self):
        ci = self.parse("0m WAV 2.png")
        self.assertEqual(ci.seconds, 0)
        self.assertTrue(ci.parseable)

    def test_case_insensitive_token(self):
        ci = self.parse("10M WAV 1.PNG")
        self.assertEqual(ci.seconds, 600)
        self.assertTrue(ci.parseable)
        self.assertEqual(ci.extension, ".PNG")  # case preserved

    def test_underscore_separator_after_minutes(self):
        ci = self.parse("10m_0 - 600 Hz.jpg")
        self.assertEqual(ci.seconds, 600)
        self.assertEqual(ci.stem, "0 - 600 Hz")
        self.assertTrue(ci.parseable)

    def test_underscore_separator_after_seconds(self):
        ci = self.parse("7m20s_0 - 441 Hz.jpg")
        self.assertEqual(ci.seconds, 7 * 60 + 20)
        self.assertEqual(ci.stem, "0 - 441 Hz")

    def test_underscore_separator_short_stem(self):
        ci = self.parse("7m_WAV 1.jpg")
        self.assertEqual(ci.seconds, 420)
        self.assertEqual(ci.stem, "WAV 1")

    def test_space_separator_still_works(self):
        ci = self.parse("11m Wav 1.jpg")
        self.assertEqual(ci.seconds, 660)
        self.assertEqual(ci.stem, "Wav 1")

    def test_bare_number_unparseable(self):
        ci = self.parse("326 WAV 1.jpg")
        self.assertIsNone(ci.seconds)
        self.assertFalse(ci.parseable)
        self.assertEqual(ci.raw_token, "326")

    def test_colon_form_unparseable(self):
        self.assertFalse(self.parse("5:26 WAV 1.jpg").parseable)

    def test_three_digit_seconds_unparseable(self):
        self.assertFalse(self.parse("5m261s WAV 1.jpg").parseable)

    def test_empty_stem_unparseable(self):
        ci = self.parse("5m26s.jpg")  # no stem after the token
        self.assertEqual(ci.seconds, 326)
        self.assertEqual(ci.stem, "")
        self.assertFalse(ci.parseable)

    def test_non_image_returns_none(self):
        self.assertIsNone(self.parse("5m26s WAV 1.wav"))
        self.assertIsNone(self.parse("notes.txt"))

    def test_jpeg_accepted(self):
        self.assertIsNotNone(self.parse("5m WAV 1.jpeg"))


# ---------------------------------------------------------------------------
# Foundational: GramFolderView bucketing
# ---------------------------------------------------------------------------

class GramFolderViewTests(IngestTestBase):

    def test_wav_and_image_buckets(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        # an already-image GLC
        (gram / "Lofar 2.glc").write_text(
            WAV_GLC.format(name="lofar-2.png"), encoding="utf-8")
        view = ingest.build_gram_folder_view(gram)
        # keys are casefolded so case drift collapses onto one bucket
        self.assertIn("wav 1", view.wav_refs)
        self.assertIn("lofar-2", view.image_refs)
        self.assertEqual(view.unreadable, [])

    def test_unreadable_isolated(self):
        gram = self.source_gram("Doc", "Gram 1")
        (gram / "bad.glc").write_text("<not-a-config", encoding="utf-8")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        view = ingest.build_gram_folder_view(gram)
        self.assertEqual(len(view.unreadable), 1)
        self.assertIn("wav 1", view.wav_refs)  # good one still indexed

    def test_has_crop_flag(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav",
                           template=WAV_GLC_CROPPED)
        view = ingest.build_gram_folder_view(gram)
        self.assertTrue(view.wav_refs["wav 1"][0].has_crop)


# ---------------------------------------------------------------------------
# US1: verify / report
# ---------------------------------------------------------------------------

class VerifyTests(IngestTestBase):

    def test_exact_match_tallied(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)

    def test_unmatched_doc_with_candidate(self):
        self.source_gram("Instructor Week 1 Grams", "Gram 1")
        self.incoming_image("Instructor Week 1 Gram", "Gram 1",
                            "5m WAV 1.png")  # missing trailing 's'
        outcomes, _ = self.run_ingest(apply=False)
        docs = self.of_kind(outcomes, ingest.KIND_UNMATCHED_DOC)
        self.assertEqual(len(docs), 1)
        self.assertIn("Instructor Week 1 Grams", docs[0].note)

    def test_unmatched_gram_with_drift_label(self):
        self.source_gram("Doc", "WAVE 1")
        self.incoming_image("Doc", "WAV 1", "5m WAV 1.png")  # token drift
        outcomes, _ = self.run_ingest(apply=False)
        grams = self.of_kind(outcomes, ingest.KIND_UNMATCHED_GRAM)
        self.assertEqual(len(grams), 1)
        self.assertEqual(grams[0].drift, ("token-drift", "WAV", "WAVE"))
        self.assertIn("token-drift('WAV' -> 'WAVE')", grams[0].note)

    def test_structurally_ambiguous_doc_zero(self):
        # doc folder exists in source but has no container subdir
        (self.source / "Doc").mkdir()
        self.incoming_image("Doc", "Gram 1", "5m WAV 1.png")
        outcomes, _ = self.run_ingest(apply=False)
        amb = self.of_kind(outcomes, ingest.KIND_AMBIGUOUS_DOC)
        self.assertEqual(len(amb), 1)
        self.assertIn("0 subdirectories", amb[0].note)

    def test_structurally_ambiguous_doc_two(self):
        self.source_gram("Doc", "Gram 1", container="Files A")
        (self.source / "Doc" / "Files B").mkdir()
        self.incoming_image("Doc", "Gram 1", "5m WAV 1.png")
        outcomes, _ = self.run_ingest(apply=False)
        amb = self.of_kind(outcomes, ingest.KIND_AMBIGUOUS_DOC)
        self.assertEqual(len(amb), 1)
        self.assertIn("2 subdirectories", amb[0].note)

    def test_flat_publication_no_container(self):
        # One publication has no "<doc> Files" tier: gram folders sit directly
        # under the doc folder. >= FLAT_DOC_MIN_GRAMS such folders => flat.
        doc = self.source / "Flat Doc"
        for n in range(1, ingest.FLAT_DOC_MIN_GRAMS + 1):
            (doc / ("Gram %d" % n)).mkdir(parents=True)
        gram1 = doc / "Gram 1"
        gram1.joinpath("Lofar 1.glc").write_text(
            WAV_GLC.format(name="WAV 1.wav"), encoding="utf-8")
        gram1.joinpath("WAV 1.wav").write_bytes(b"RIFF")
        self.incoming_image("Flat Doc", "Gram 1", "5m26s WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        self.assertEqual(tally.counts.get(ingest.KIND_AMBIGUOUS_DOC, 0), 0)

    def test_below_flat_threshold_still_ambiguous(self):
        # A handful of sub-folders (below the flat threshold, not a single
        # container) stays ambiguous — we won't guess the layout.
        doc = self.source / "Doc"
        for n in range(1, 4):  # 3 subdirs
            (doc / ("Thing %d" % n)).mkdir(parents=True)
        self.incoming_image("Doc", "Thing 1", "5m WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_AMBIGUOUS_DOC), 1)

    def test_unparseable_survey(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "wibble WAV 1.png")
        outcomes, _ = self.run_ingest(apply=False)
        up = self.of_kind(outcomes, ingest.KIND_UNPARSEABLE)
        self.assertEqual(len(up), 1)
        self.assertIn('token "wibble"', up[0].note)

    def test_unmatched_image_lists_wavs(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m NOPE 9.png")
        outcomes, _ = self.run_ingest(apply=False)
        um = self.of_kind(outcomes, ingest.KIND_UNMATCHED_IMAGE)
        self.assertEqual(len(um), 1)
        self.assertIn("WAV 1", um[0].note)

    def test_token_drift_trend_aggregation(self):
        for n in (1, 2, 3):
            self.source_gram("Doc", "WAVE %d" % n)
            self.incoming_image("Doc", "WAV %d" % n, "5m WAV %d.png" % n)
        outcomes, _ = self.run_ingest(apply=False)
        trends = ingest._aggregate_trends(outcomes)
        self.assertIn("token-drift 'WAV' -> 'WAVE' x 3", trends)

    def test_report_is_deterministic(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        o1, t1 = self.run_ingest(apply=False)
        o2, t2 = self.run_ingest(apply=False)
        r1 = ingest.render_report(o1, t1, incoming_root=self.incoming,
                                  source_root=self.source, apply=False)
        r2 = ingest.render_report(o2, t2, incoming_root=self.incoming,
                                  source_root=self.source, apply=False)
        self.assertEqual(r1, r2)

    def test_verify_is_read_only(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        src_before = self.snapshot(self.source)
        inc_before = self.snapshot(self.incoming)
        self.run_ingest(apply=False)
        self.assertEqual(self.snapshot(self.source), src_before)
        self.assertEqual(self.snapshot(self.incoming), inc_before)


# ---------------------------------------------------------------------------
# Case-insensitive matching (folders + stems) and the underscore separator
# ---------------------------------------------------------------------------

class CaseInsensitiveMatchTests(IngestTestBase):

    def test_case_insensitive_folder_match(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        # incoming doc AND gram folders differ only in case
        self.incoming_image("DOC", "GRAM 1", "5m26s WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        self.assertEqual(tally.counts.get(ingest.KIND_UNMATCHED_DOC, 0), 0)
        self.assertEqual(tally.counts.get(ingest.KIND_UNMATCHED_GRAM, 0), 0)

    def test_case_insensitive_stem_match(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "Wav 1.wav")  # mixed-case wav
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")  # upper stem
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)

    def test_underscore_and_case_apply_uses_wav_casing(self):
        gram = self.source_gram("Doc", "Gram 1")
        glc = self.write_wav_glc(gram, "Lofar 1.glc", "Wav 1.wav")
        # underscore separator AND upper-case stem, as in the real data
        self.incoming_image("Doc", "Gram 1", "7m_WAV 1.jpg")
        self.run_ingest(apply=True)
        # copy takes the WAV's casing, not the incoming screenshot's
        self.assertTrue((gram / "Wav 1.jpg").exists())
        self.assertFalse((gram / "WAV 1.jpg").exists())
        doc = parse_glc(glc)
        self.assertEqual(doc.image_filename, "Wav 1.jpg")
        # The tool still inserts the duration as <bottom_crop> (7m = 420 s);
        # extract no longer reads it for time_end (that now comes from the
        # image height, issue #148), so assert on the raw GLC text.
        self.assertIn("<bottom_crop>420</bottom_crop>",
                      glc.read_text(encoding="utf-8"))

    def test_descriptive_stem_with_underscore(self):
        gram = self.source_gram("Doc", "Gram 1")
        glc = self.write_wav_glc(gram, "Lofar 1.glc", "0 - 600 Hz.wav")
        self.incoming_image("Doc", "Gram 1", "10m_0 - 600 Hz.jpg")
        self.run_ingest(apply=True)
        self.assertTrue((gram / "0 - 600 Hz.jpg").exists())
        # 10m = 600 s inserted as <bottom_crop> (unused by extract now, #148).
        self.assertIn("<bottom_crop>600</bottom_crop>",
                      glc.read_text(encoding="utf-8"))

    def test_two_case_variant_images_are_ambiguous(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "Wav 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m WAV 1.png")
        self.incoming_image("Doc", "Gram 1", "6m wav 1.jpg")
        before = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.counts.get(ingest.KIND_AMBIGUOUS), 1)
        self.assertEqual(self.snapshot(self.source), before)


# ---------------------------------------------------------------------------
# US2: apply
# ---------------------------------------------------------------------------

class ApplyTests(IngestTestBase):

    def _matched_gram(self, wav="WAV 1.wav", glc="Lofar 1.glc",
                      image="5m26s WAV 1.png"):
        gram = self.source_gram("Doc", "Gram 1")
        glc_path = self.write_wav_glc(gram, glc, wav)
        img = self.incoming_image("Doc", "Gram 1", image)
        return gram, glc_path, img

    def test_image_copied_under_wav_stem(self):
        gram, _, img = self._matched_gram()
        self.run_ingest(apply=True)
        copied = gram / "WAV 1.png"
        self.assertTrue(copied.exists())
        self.assertEqual(copied.read_bytes(), img.read_bytes())

    def test_stale_copy_overwritten(self):
        gram, _, img = self._matched_gram()
        (gram / "WAV 1.png").write_bytes(b"STALE")
        self.run_ingest(apply=True)
        self.assertEqual((gram / "WAV 1.png").read_bytes(), img.read_bytes())

    def test_glc_rewritten_and_crop_inserted(self):
        gram, glc_path, _ = self._matched_gram()
        before = glc_path.read_text(encoding="utf-8")
        self.run_ingest(apply=True)
        after = glc_path.read_text(encoding="utf-8")
        self.assertNotEqual(before, after)
        # downstream contract: parse_glc reads the new image filename; the
        # inserted <bottom_crop> (326) is verified as raw text below and by
        # test_crop_block_indentation — extract derives time_end from the
        # image height now, not this value (issue #148).
        doc = parse_glc(glc_path)
        self.assertEqual(doc.image_filename, "WAV 1.png")
        self.assertIn("<bottom_crop>326</bottom_crop>", after)

    def test_crop_block_indentation(self):
        gram, glc_path, _ = self._matched_gram()
        self.run_ingest(apply=True)
        text = glc_path.read_text(encoding="utf-8")
        self.assertIn("    <bitmap_crop_values>\n"
                      "      <bottom_crop>326</bottom_crop>\n"
                      "    </bitmap_crop_values>", text)

    def test_only_filename_and_crop_changed(self):
        gram, glc_path, _ = self._matched_gram()
        before = glc_path.read_text(encoding="utf-8")
        self.run_ingest(apply=True)
        after = glc_path.read_text(encoding="utf-8")
        # removing the crop block and reverting the filename yields the original
        reverted = after.replace(
            "\n    <bitmap_crop_values>\n"
            "      <bottom_crop>326</bottom_crop>\n"
            "    </bitmap_crop_values>", "")
        reverted = reverted.replace(
            "<filename>WAV 1.png</filename>",
            "<filename>W:\\aaac\\WAV 1.wav</filename>")
        self.assertEqual(reverted, before)

    def test_wav_left_in_place(self):
        gram, _, _ = self._matched_gram()
        wav_before = (gram / "WAV 1.wav").read_bytes()
        self.run_ingest(apply=True)
        self.assertTrue((gram / "WAV 1.wav").exists())
        self.assertEqual((gram / "WAV 1.wav").read_bytes(), wav_before)

    def test_two_glcs_share_one_wav(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        # second GLC references the same wav
        (gram / "Lofar 2.glc").write_text(
            WAV_GLC.format(name="W:\\aaac\\WAV 1.wav"), encoding="utf-8")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        _, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.images_copied, 1)
        self.assertEqual(tally.glcs_rewritten, 2)

    def test_reapply_is_noop(self):
        gram, glc_path, _ = self._matched_gram()
        self.run_ingest(apply=True)
        after_first = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(self.snapshot(self.source), after_first)
        self.assertEqual(tally.counts.get(ingest.KIND_ALREADY), 1)
        self.assertEqual(tally.images_copied, 0)

    def test_verify_clean_after_apply(self):
        self._matched_gram()
        self.run_ingest(apply=True)
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED, 0), 0)
        self.assertEqual(tally.counts.get(ingest.KIND_ALREADY), 1)

    def test_apply_leaves_incoming_untouched(self):
        self._matched_gram()
        inc_before = self.snapshot(self.incoming)
        self.run_ingest(apply=True)
        self.assertEqual(self.snapshot(self.incoming), inc_before)


# ---------------------------------------------------------------------------
# US3: ambiguity + guard classes
# ---------------------------------------------------------------------------

class AmbiguityTests(IngestTestBase):

    def test_two_images_one_wav_ambiguous(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        self.incoming_image("Doc", "Gram 1", "6m WAV 1.jpg")
        before = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=True)
        amb = self.of_kind(outcomes, ingest.KIND_AMBIGUOUS)
        self.assertEqual(len(amb), 1)
        self.assertIn("5m26s WAV 1.png", amb[0].note)
        self.assertIn("6m WAV 1.jpg", amb[0].note)
        self.assertEqual(self.snapshot(self.source), before)  # nothing applied

    def test_already_cropped_glc_untouched_sibling_rewritten(self):
        gram = self.source_gram("Doc", "Gram 1")
        # one already-cropped wav GLC, one normal wav GLC, same wav
        cropped = self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav",
                                     template=WAV_GLC_CROPPED)
        normal = self.write_wav_glc(gram, "Lofar 2.glc", "WAV 1.wav")
        cropped_before = cropped.read_text(encoding="utf-8")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        outcomes, tally = self.run_ingest(apply=True)
        # cropped GLC byte-identical; normal GLC rewritten
        self.assertEqual(cropped.read_text(encoding="utf-8"), cropped_before)
        self.assertEqual(parse_glc(normal).image_filename, "WAV 1.png")
        self.assertEqual(tally.counts.get(ingest.KIND_GLC_CROPPED), 1)
        self.assertEqual(tally.glcs_rewritten, 1)

    def test_unreadable_glc_isolated_other_converts(self):
        gram = self.source_gram("Doc", "Gram 1")
        (gram / "bad.glc").write_text("<broken", encoding="utf-8")
        good = self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.counts.get(ingest.KIND_GLC_UNREADABLE), 1)
        self.assertEqual(parse_glc(good).image_filename, "WAV 1.png")

    def test_summary_enumerates_all_classes(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "5m26s WAV 1.png")
        _, tally = self.run_ingest(apply=False)
        line = ingest._summary_line(tally, apply=False)
        for kind in (ingest.KIND_UNMATCHED_DOC, ingest.KIND_AMBIGUOUS,
                     ingest.KIND_ALREADY, ingest.KIND_GLC_CROPPED):
            self.assertIn(kind, line)


# ---------------------------------------------------------------------------
# Drift labelling unit tests
# ---------------------------------------------------------------------------

class DriftLabelTests(unittest.TestCase):

    def test_case_only(self):
        self.assertEqual(ingest.drift_label("gram 1", "Gram 1"),
                         ("case-only", None, None))

    def test_whitespace_only(self):
        self.assertEqual(ingest.drift_label("Gram  1", "Gram 1"),
                         ("whitespace-only", None, None))

    def test_token_drift(self):
        self.assertEqual(ingest.drift_label("WAV 1", "WAVE 1"),
                         ("token-drift", "WAV", "WAVE"))

    def test_other(self):
        self.assertEqual(ingest.drift_label("Gram8", "Gram 1"),
                         ("other", None, None))

    def test_none_when_no_candidate(self):
        self.assertIsNone(ingest.drift_label("Gram 1", None))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
