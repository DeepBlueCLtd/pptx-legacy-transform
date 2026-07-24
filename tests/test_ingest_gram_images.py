"""Tests for ingest_gram_images.py.

Exercises the two-phase import of author-supplied gram screenshots: whole-stem
matching (no duration parsing -- issue #148 measures the time period from the
image height), the case- and hyphen-spacing-tolerant match key, container
resolution, folder/stem matching with nearest-candidate suggestions and trend
grouping, the read-only verify guarantee, the apply-mode GLC filename rewrite +
image copy (wav deliberately left in place), idempotency, demon-image handling
(including numbered ``Demon2-`` tokens), and every warn-and-skip class.
Stdlib-only.
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
# Foundational: filename parsing (whole stem, no duration) + extension gate
# ---------------------------------------------------------------------------

class ImageFilenameParsingTests(IngestTestBase):

    def parse(self, name: str):
        return ingest.parse_image_filename(Path(name))

    def test_whole_stem_is_the_match_stem(self):
        ci = self.parse("WAV 1.jpg")
        self.assertEqual(ci.stem, "WAV 1")
        self.assertEqual(ci.extension, ".jpg")

    def test_frequency_range_stem_kept_intact(self):
        # The reported failing case: "0 - 1322 Hz" must not be split on the
        # leading "0 -" (which the old duration parser mistook for a token).
        ci = self.parse("0 - 1322 Hz.jpg")
        self.assertEqual(ci.stem, "0 - 1322 Hz")

    def test_no_space_frequency_range(self):
        ci = self.parse("0-1000 Hz.png")
        self.assertEqual(ci.stem, "0-1000 Hz")

    def test_leading_digit_stem_kept(self):
        # "WAV 2" is kept whole -- the old parser split it into token "WAV".
        ci = self.parse("WAV 2.png")
        self.assertEqual(ci.stem, "WAV 2")

    def test_extension_case_preserved(self):
        self.assertEqual(self.parse("WAV 1.PNG").extension, ".PNG")

    def test_non_image_returns_none(self):
        self.assertIsNone(self.parse("WAV 1.wav"))
        self.assertIsNone(self.parse("notes.txt"))

    def test_jpeg_accepted(self):
        self.assertIsNotNone(self.parse("WAV 1.jpeg"))


# ---------------------------------------------------------------------------
# The tolerant match key (case + hyphen spacing)
# ---------------------------------------------------------------------------

class MatchKeyTests(unittest.TestCase):

    def test_case_folds(self):
        self.assertEqual(ingest.match_key("WAV 2"), ingest.match_key("Wav 2"))

    def test_hyphen_spacing_collapses_both_directions(self):
        # "0 - 1000 Hz", "0-1000 Hz" and "0- 1000 Hz" all fold together.
        keys = {ingest.match_key(s) for s in
                ("0 - 1000 Hz", "0-1000 Hz", "0- 1000 Hz", "0 -1000 Hz")}
        self.assertEqual(len(keys), 1)

    def test_internal_whitespace_collapses(self):
        self.assertEqual(ingest.match_key("WAV  1"), ingest.match_key("WAV 1"))

    def test_genuine_drift_stays_distinct(self):
        # A different token or a missing digit is real drift, not folded away.
        self.assertNotEqual(ingest.match_key("WAV 1"), ingest.match_key("WAVE 1"))
        self.assertNotEqual(ingest.match_key("0 - 1000 Hz"),
                            ingest.match_key("0 - 1100 Hz"))


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
        # keys run through match_key so case/hyphen drift collapses onto one key
        self.assertIn(ingest.match_key("WAV 1"), view.wav_refs)
        self.assertIn(ingest.match_key("lofar-2"), view.image_refs)
        self.assertEqual(view.unreadable, [])

    def test_hyphen_spaced_wav_key(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "0-1000 Hz.wav")
        view = ingest.build_gram_folder_view(gram)
        # the space-flavoured spelling resolves to the same bucket
        self.assertIn(ingest.match_key("0 - 1000 Hz"), view.wav_refs)

    def test_unreadable_isolated(self):
        gram = self.source_gram("Doc", "Gram 1")
        (gram / "bad.glc").write_text("<not-a-config", encoding="utf-8")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        view = ingest.build_gram_folder_view(gram)
        self.assertEqual(len(view.unreadable), 1)
        self.assertIn(ingest.match_key("WAV 1"), view.wav_refs)  # good one kept


# ---------------------------------------------------------------------------
# US1: verify / report
# ---------------------------------------------------------------------------

class VerifyTests(IngestTestBase):

    def test_exact_match_tallied(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)

    def test_unmatched_doc_with_candidate(self):
        self.source_gram("Instructor Week 1 Grams", "Gram 1")
        self.incoming_image("Instructor Week 1 Gram", "Gram 1",
                            "WAV 1.png")  # doc missing trailing 's'
        outcomes, _ = self.run_ingest(apply=False)
        docs = self.of_kind(outcomes, ingest.KIND_UNMATCHED_DOC)
        self.assertEqual(len(docs), 1)
        self.assertIn("Instructor Week 1 Grams", docs[0].note)

    def test_unmatched_gram_with_drift_label(self):
        self.source_gram("Doc", "WAVE 1")
        self.incoming_image("Doc", "WAV 1", "WAV 1.png")  # token drift
        outcomes, _ = self.run_ingest(apply=False)
        grams = self.of_kind(outcomes, ingest.KIND_UNMATCHED_GRAM)
        self.assertEqual(len(grams), 1)
        self.assertEqual(grams[0].drift, ("token-drift", "WAV", "WAVE"))
        self.assertIn("token-drift('WAV' -> 'WAVE')", grams[0].note)

    def test_structurally_ambiguous_doc_zero(self):
        # doc folder exists in source but has no container subdir
        (self.source / "Doc").mkdir()
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
        outcomes, _ = self.run_ingest(apply=False)
        amb = self.of_kind(outcomes, ingest.KIND_AMBIGUOUS_DOC)
        self.assertEqual(len(amb), 1)
        self.assertIn("0 subdirectories", amb[0].note)

    def test_structurally_ambiguous_doc_two(self):
        self.source_gram("Doc", "Gram 1", container="Files A")
        (self.source / "Doc" / "Files B").mkdir()
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
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
        self.incoming_image("Flat Doc", "Gram 1", "WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        self.assertEqual(tally.counts.get(ingest.KIND_AMBIGUOUS_DOC, 0), 0)

    def test_below_flat_threshold_still_ambiguous(self):
        # A handful of sub-folders (below the flat threshold, not a single
        # container) stays ambiguous — we won't guess the layout.
        doc = self.source / "Doc"
        for n in range(1, 4):  # 3 subdirs
            (doc / ("Thing %d" % n)).mkdir(parents=True)
        self.incoming_image("Doc", "Thing 1", "WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_AMBIGUOUS_DOC), 1)

    def test_unmatched_image_lists_wavs(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "NOPE 9.png")
        outcomes, _ = self.run_ingest(apply=False)
        um = self.of_kind(outcomes, ingest.KIND_UNMATCHED_IMAGE)
        self.assertEqual(len(um), 1)
        self.assertIn("WAV 1", um[0].note)

    def test_token_drift_trend_aggregation(self):
        for n in (1, 2, 3):
            self.source_gram("Doc", "WAVE %d" % n)
            self.incoming_image("Doc", "WAV %d" % n, "WAV %d.png" % n)
        outcomes, _ = self.run_ingest(apply=False)
        trends = ingest._aggregate_trends(outcomes)
        self.assertIn("token-drift 'WAV' -> 'WAVE' x 3", trends)

    def test_report_is_deterministic(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
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
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
        src_before = self.snapshot(self.source)
        inc_before = self.snapshot(self.incoming)
        self.run_ingest(apply=False)
        self.assertEqual(self.snapshot(self.source), src_before)
        self.assertEqual(self.snapshot(self.incoming), inc_before)


# ---------------------------------------------------------------------------
# Tolerant matching: case + hyphen spacing (the reported unmatched patterns)
# ---------------------------------------------------------------------------

class TolerantMatchTests(IngestTestBase):

    def _match_one(self, wav_name: str, image_name: str):
        gram = self.source_gram("Doc", "Gram 1")
        glc = self.write_wav_glc(gram, "Lofar 1.glc", wav_name)
        self.incoming_image("Doc", "Gram 1", image_name)
        outcomes, tally = self.run_ingest(apply=True)
        return gram, glc, tally

    def test_case_insensitive_stem_match(self):
        # incoming "WAV 2" vs source "Wav 2.wav"
        gram, glc, tally = self._match_one("Wav 2.wav", "WAV 2.png")
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        # copy takes the wav's own casing
        self.assertTrue((gram / "Wav 2.png").exists())
        self.assertEqual(parse_glc(glc).image_filename, "Wav 2.png")

    def test_spaces_removed_around_minus(self):
        # incoming "0 - 1000 Hz" vs source "0-1000 Hz.wav"
        gram, glc, tally = self._match_one("0-1000 Hz.wav", "0 - 1000 Hz.jpg")
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        # copy takes the wav's own spacing
        self.assertTrue((gram / "0-1000 Hz.jpg").exists())
        self.assertEqual(parse_glc(glc).image_filename, "0-1000 Hz.jpg")

    def test_spaces_added_around_minus(self):
        # incoming "0-1100 Hz" vs source "0 - 1100 Hz.wav"
        gram, glc, tally = self._match_one("0 - 1100 Hz.wav", "0-1100 Hz.jpg")
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        self.assertTrue((gram / "0 - 1100 Hz.jpg").exists())
        self.assertEqual(parse_glc(glc).image_filename, "0 - 1100 Hz.jpg")

    def test_exact_frequency_range_match(self):
        # the previously-"unparseable" case now matches directly
        gram, glc, tally = self._match_one("0 - 1322 Hz.wav", "0 - 1322 Hz.jpg")
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        self.assertTrue((gram / "0 - 1322 Hz.jpg").exists())

    def test_case_insensitive_folder_match(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        # incoming doc AND gram folders differ only in case
        self.incoming_image("DOC", "GRAM 1", "WAV 1.png")
        outcomes, tally = self.run_ingest(apply=False)
        self.assertEqual(tally.counts.get(ingest.KIND_MATCHED), 1)
        self.assertEqual(tally.counts.get(ingest.KIND_UNMATCHED_DOC, 0), 0)
        self.assertEqual(tally.counts.get(ingest.KIND_UNMATCHED_GRAM, 0), 0)

    def test_no_bottom_crop_written(self):
        # The time period is image-derived (issue #148); the GLC gets only a
        # repointed <filename>, never a <bitmap_crop_values> block.
        gram, glc, _ = self._match_one("WAV 1.wav", "WAV 1.png")
        self.assertNotIn("bitmap_crop_values", glc.read_text(encoding="utf-8"))
        self.assertNotIn("bottom_crop", glc.read_text(encoding="utf-8"))

    def test_two_variant_images_are_ambiguous(self):
        # A case variant and a hyphen-spacing variant both fold onto one wav:
        # neither is applied.
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "0 - 40 Hz.wav")
        self.incoming_image("Doc", "Gram 1", "0-40 Hz.png")
        self.incoming_image("Doc", "Gram 1", "0 - 40 hz.jpg")
        before = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.counts.get(ingest.KIND_AMBIGUOUS), 1)
        self.assertEqual(self.snapshot(self.source), before)


# ---------------------------------------------------------------------------
# US2: apply
# ---------------------------------------------------------------------------

class ApplyTests(IngestTestBase):

    def _matched_gram(self, wav="WAV 1.wav", glc="Lofar 1.glc",
                      image="WAV 1.png"):
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

    def test_glc_filename_rewritten_no_crop(self):
        gram, glc_path, _ = self._matched_gram()
        before = glc_path.read_text(encoding="utf-8")
        self.run_ingest(apply=True)
        after = glc_path.read_text(encoding="utf-8")
        self.assertNotEqual(before, after)
        doc = parse_glc(glc_path)
        self.assertEqual(doc.image_filename, "WAV 1.png")
        self.assertNotIn("bitmap_crop_values", after)

    def test_only_filename_changed(self):
        gram, glc_path, _ = self._matched_gram()
        before = glc_path.read_text(encoding="utf-8")
        self.run_ingest(apply=True)
        after = glc_path.read_text(encoding="utf-8")
        # reverting the filename yields the original, byte-for-byte
        reverted = after.replace(
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
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
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
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
        self.incoming_image("Doc", "Gram 1", "WAV 1.jpg")
        before = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=True)
        amb = self.of_kind(outcomes, ingest.KIND_AMBIGUOUS)
        self.assertEqual(len(amb), 1)
        self.assertIn("WAV 1.png", amb[0].note)
        self.assertIn("WAV 1.jpg", amb[0].note)
        self.assertEqual(self.snapshot(self.source), before)  # nothing applied

    def test_image_matches_two_wavs_ambiguous(self):
        # Two wavs differing only in hyphen spacing fold onto one key; an
        # incoming image matching that key is not applied to either.
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "0 - 40 Hz.wav")
        self.write_wav_glc(gram, "Lofar 2.glc", "0-40 Hz.wav")
        self.incoming_image("Doc", "Gram 1", "0 - 40 Hz.png")
        before = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=True)
        amb = self.of_kind(outcomes, ingest.KIND_AMBIGUOUS)
        self.assertEqual(len(amb), 1)
        self.assertIn("2 wavs", amb[0].note)
        self.assertEqual(self.snapshot(self.source), before)

    def test_unreadable_glc_isolated_other_converts(self):
        gram = self.source_gram("Doc", "Gram 1")
        (gram / "bad.glc").write_text("<broken", encoding="utf-8")
        good = self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.counts.get(ingest.KIND_GLC_UNREADABLE), 1)
        self.assertEqual(parse_glc(good).image_filename, "WAV 1.png")

    def test_summary_enumerates_all_classes(self):
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
        _, tally = self.run_ingest(apply=False)
        line = ingest._summary_line(tally, apply=False)
        for kind in (ingest.KIND_UNMATCHED_DOC, ingest.KIND_AMBIGUOUS,
                     ingest.KIND_ALREADY, ingest.KIND_UNMATCHED_IMAGE):
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


# ---------------------------------------------------------------------------
# Demon images (issue #151)
# ---------------------------------------------------------------------------

class DemonGlcTextTests(unittest.TestCase):
    """The targeted demon.glc rewrite: repoint filename + bake 0-40 Hz band."""

    def test_repoints_filename_and_bakes_band(self):
        out = ingest.build_demon_glc_text(
            WAV_GLC.format(name="WAV 1.wav"), "Demon - 0-40Hz.png")
        self.assertIn("<filename>Demon - 0-40Hz.png</filename>", out)
        self.assertIn("<bandwidth>40</bandwidth>", out)
        self.assertIn("<bandcentre>20</bandcentre>", out)
        # Original band values are gone.
        self.assertNotIn("<bandwidth>400</bandwidth>", out)
        self.assertNotIn("<bandcentre>200</bandcentre>", out)

    def test_no_bottom_crop_inserted(self):
        out = ingest.build_demon_glc_text(
            WAV_GLC.format(name="WAV 1.wav"), "Demon - 0-40Hz.png")
        self.assertNotIn("bitmap_crop_values", out)

    def test_parses_to_expected_glc(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "demon.glc"
            p.write_text(ingest.build_demon_glc_text(
                WAV_GLC.format(name="WAV 1.wav"), "Demon - 0-40Hz.png"),
                encoding="utf-8")
            glc = parse_glc(p)
            self.assertEqual(glc.image_filename, "Demon - 0-40Hz.png")
            self.assertEqual(glc.bandwidth, "40")
            self.assertEqual(glc.bandcentre, "20")

    def test_missing_band_raises(self):
        no_band = (
            "<GAPS_Lite_configuration><data_source>"
            "<filename>x.wav</filename></data_source>"
            "</GAPS_Lite_configuration>")
        with self.assertRaises(ValueError):
            ingest.build_demon_glc_text(no_band, "Demon.png")

    def test_missing_filename_raises(self):
        no_fn = (
            "<GAPS_Lite_configuration><settings><lofar>"
            "<bandwidth>1</bandwidth><bandcentre>1</bandcentre>"
            "</lofar></settings></GAPS_Lite_configuration>")
        with self.assertRaises(ValueError):
            ingest.build_demon_glc_text(no_fn, "Demon.png")


class DemonImageTests(IngestTestBase):

    def _demon_gram(self, *, demon_names):
        """source gram with one wav-backed lofar; incoming holds demon(s)."""
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        for name in demon_names:
            self.incoming_image("Doc", "Gram 1", name)
        return gram

    def test_verify_reports_demon_read_only(self):
        gram = self._demon_gram(demon_names=["Demon - 0-40Hz.png"])
        before = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=False)
        demons = self.of_kind(outcomes, ingest.KIND_DEMON)
        self.assertEqual(len(demons), 1)
        # nothing written in verify
        self.assertEqual(self.snapshot(self.source), before)
        self.assertFalse((gram / "demon.glc").exists())

    def test_apply_creates_marker_and_copies_image(self):
        gram = self._demon_gram(demon_names=["Demon - 10m2s 0-40Hz.png"])
        outcomes, tally = self.run_ingest(apply=True)
        marker = gram / "demon.glc"
        image = gram / "Demon - 10m2s 0-40Hz.png"
        self.assertTrue(marker.exists())
        self.assertTrue(image.exists())  # original name preserved
        glc = parse_glc(marker)
        self.assertEqual(glc.image_filename, "Demon - 10m2s 0-40Hz.png")
        self.assertEqual(glc.bandwidth, "40")
        self.assertEqual(glc.bandcentre, "20")
        self.assertEqual(tally.demon_markers, 1)

    def test_apply_idempotent(self):
        gram = self._demon_gram(demon_names=["Demon - 0-40Hz.png"])
        self.run_ingest(apply=True)
        after_first = self.snapshot(self.source)
        outcomes, tally = self.run_ingest(apply=True)
        # second run makes no change and reports "already present"
        self.assertEqual(self.snapshot(self.source), after_first)
        self.assertEqual(tally.demon_markers, 0)
        note = self.of_kind(outcomes, ingest.KIND_DEMON)[0].note
        self.assertIn("already present", note)

    def test_multiple_demons_numbered_markers(self):
        gram = self._demon_gram(
            demon_names=["Demon - 0-40Hz.png", "Demon - 10m2s 0-40Hz.png"])
        self.run_ingest(apply=True)
        self.assertTrue((gram / "demon.glc").exists())
        self.assertTrue((gram / "demon-2.glc").exists())
        # deterministic: first marker -> first image by sorted name
        first = parse_glc(gram / "demon.glc")
        second = parse_glc(gram / "demon-2.glc")
        self.assertEqual(first.image_filename, "Demon - 0-40Hz.png")
        self.assertEqual(second.image_filename, "Demon - 10m2s 0-40Hz.png")

    def test_duration_prefixed_demon_name(self):
        # A demon filename may carry a leading duration token before "Demon"
        # (e.g. "4m10s_Demon - 0 - 40 Hz.jpg"). The duration is decorative.
        gram = self._demon_gram(demon_names=["4m10s_Demon - 0 - 40 Hz.jpg"])
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.demon_markers, 1)
        marker = gram / "demon.glc"
        self.assertTrue(marker.exists())
        self.assertEqual(
            parse_glc(marker).image_filename, "4m10s_Demon - 0 - 40 Hz.jpg")
        self.assertTrue((gram / "4m10s_Demon - 0 - 40 Hz.jpg").exists())

    def test_numbered_demon_token(self):
        # A "Demon2-" token (the digit rides straight after "Demon", no space)
        # must be recognised as a demon -- the reported miss.
        gram = self._demon_gram(demon_names=["Demon2- 0 - 40 Hz.jpg"])
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.demon_markers, 1)
        self.assertTrue((gram / "demon.glc").exists())
        self.assertTrue((gram / "Demon2- 0 - 40 Hz.jpg").exists())
        # never mis-reported as an ordinary unmatched image
        self.assertEqual(self.of_kind(outcomes, ingest.KIND_UNMATCHED_IMAGE), [])

    def test_prefix_regex_matches_expected_shapes(self):
        match = lambda s: bool(ingest.DEMON_PREFIX_RE.match(s))
        self.assertTrue(match("Demon - 0-40Hz"))
        self.assertTrue(match("Demon - 10m2s 0-40Hz"))
        self.assertTrue(match("4m10s_Demon - 0 - 40 Hz"))
        self.assertTrue(match("21m Demon - 0-40Hz"))
        # numbered demons (the reported miss)
        self.assertTrue(match("Demon2- 0 - 40 Hz"))
        self.assertTrue(match("Demon2- 9m_0 - 40 Hz"))
        self.assertTrue(match("Demon3 - 0-40Hz"))
        # not a demon: ordinary wav-replacement screenshots or "Demon"-words
        self.assertFalse(match("WAV 1"))
        self.assertFalse(match("0 - 1322 Hz"))
        self.assertFalse(match("Demonstrate"))

    def test_demon_not_matched_as_wav(self):
        # A demon image must never be reported as an unmatched image.
        self._demon_gram(demon_names=["Demon - 0-40Hz.png"])
        outcomes, _ = self.run_ingest(apply=False)
        self.assertEqual(self.of_kind(outcomes, ingest.KIND_UNMATCHED_IMAGE), [])

    def test_no_template_glc_skips(self):
        # Gram folder with a demon incoming but no hyperlinked .glc to clone.
        self.source_gram("Doc", "Gram 1")  # empty gram folder
        self.incoming_image("Doc", "Gram 1", "Demon - 0-40Hz.png")
        outcomes, tally = self.run_ingest(apply=True)
        self.assertEqual(tally.demon_markers, 0)
        note = self.of_kind(outcomes, ingest.KIND_DEMON)[0].note
        self.assertIn("no hyperlinked", note)

    def test_demon_alongside_wav_replacement(self):
        # A folder can carry both a normal wav-replacement screenshot and a demon.
        gram = self.source_gram("Doc", "Gram 1")
        self.write_wav_glc(gram, "Lofar 1.glc", "WAV 1.wav")
        self.incoming_image("Doc", "Gram 1", "WAV 1.png")
        self.incoming_image("Doc", "Gram 1", "Demon - 0-40Hz.png")
        outcomes, tally = self.run_ingest(apply=True)
        # wav replacement applied AND demon seeded
        self.assertEqual(tally.demon_markers, 1)
        self.assertGreaterEqual(tally.counts.get(ingest.KIND_MATCHED, 0), 1)
        self.assertTrue((gram / "demon.glc").exists())
        self.assertTrue((gram / "WAV 1.png").exists())  # wav replacement copy


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
