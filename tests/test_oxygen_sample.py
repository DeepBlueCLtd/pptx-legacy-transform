"""Tests for the committed Oxygen sample publication (demo/oxygen-sample/).

The sample is a miniature ``main`` + ``progress-test-1`` publication whose
generated DITA tree is **committed** — the one deliberate exception to the
"``dita/`` is not committed" rule — so the technical author can open it
straight in Oxygen's Responsive WebHelp template and publish by hand without
first running Python. Because it is committed, it can silently drift from the
generator that produced it; ``test_committed_tree_matches_a_fresh_run`` is what
stops that.

Everything here regenerates from the committed ``sample.csv`` into a temp dir
and asserts on *that*, so a failure always names the fix: re-run
``python demo/oxygen-sample/regenerate.py`` and commit the result.
"""

from __future__ import annotations

import csv
import filecmp
import shutil
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import extract_to_csv  # noqa: E402
import generate_dita  # noqa: E402


SAMPLE = REPO_ROOT / "demo" / "oxygen-sample"
SAMPLE_CSV = SAMPLE / "sample.csv"
COMMITTED_DITA = SAMPLE / "dita"
TMP = REPO_ROOT / "tests" / "_tmp"

REGENERATE = "python demo/oxygen-sample/regenerate.py"

# Mirrors demo/oxygen-sample/regenerate.py. Kept in step by
# ``test_regenerate_wrapper_matches_this_harness`` below, so the snapshot this
# suite compares against is the one the documented command produces.
STATIC_ROOT = REPO_ROOT / "static"
SEVEN_QUESTIONS_PNG = REPO_ROOT / "7_questions.png"


def _rows() -> "list[dict]":
    with SAMPLE_CSV.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _files(root: Path) -> "set[str]":
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def _sections(topic: Path) -> "list[tuple[str, str, str]]":
    """``(outputclass, id, title)`` for every section in a gram topic, in order."""
    out = []
    for section in ET.parse(topic).getroot().iter("section"):
        title = section.find("title")
        out.append((section.get("outputclass") or "", section.get("id") or "",
                    (title.text or "") if title is not None else ""))
    return out


class OxygenSampleTests(unittest.TestCase):
    """Regenerate the sample once, then assert on the fresh tree."""

    out: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.out = TMP / "oxygen_sample"
        if cls.out.exists():
            shutil.rmtree(cls.out)
        cls.out.parent.mkdir(parents=True, exist_ok=True)
        rc = generate_dita.main([
            "--csv", str(SAMPLE_CSV),
            "--out", str(cls.out),
            "--image-root", str(REPO_ROOT),
            "--static-root", str(STATIC_ROOT),
            "--seven-questions", str(SEVEN_QUESTIONS_PNG),
        ])
        cls.rc = rc

    # -- the CSV contract ---------------------------------------------------

    def test_csv_header_is_the_extract_schema_plus_the_dedupe_columns(self):
        """The sample is a real pipeline artefact, not a bespoke file format.

        It is ``extract_to_csv.py`` output carried through
        ``deduplicate_csv.py --no-dedupe --main-numbering per-week``, so its
        header is the 21-column extract schema with that script's two
        right-edge additions.
        """
        with SAMPLE_CSV.open(encoding="utf-8-sig", newline="") as fh:
            header = tuple(csv.reader(fh).__next__())
        self.assertEqual(
            header,
            extract_to_csv.CSV_COLUMNS + ("master_png_path", "target_gram_id"),
        )

    def test_csv_passes_the_generator_fail_fast_gates(self):
        """A duplicate identity tuple only *warns* in the generator — it would
        silently merge two grams into one topic — so assert it here instead of
        trusting the log."""
        rows = _rows()
        self.assertEqual(generate_dita.check_row_identity(rows), [])
        self.assertEqual(generate_dita.check_main_chapter_assigned(rows), [])

    def test_csv_is_written_utf8_bom_crlf(self):
        """Excel's encoding detection depends on it (see README's CSV notes)."""
        raw = SAMPLE_CSV.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"\r\n", raw)

    def test_every_referenced_asset_is_committed(self):
        """``--image-root`` is the repo root, so every asset cell must resolve
        against a file already in the repo — otherwise the committed tree
        carries a dangling href that only shows up in Oxygen."""
        for row in _rows():
            for column in ("png_path", "glc_path", "analysis_doc_path"):
                rel = (row.get(column) or "").strip()
                if rel:
                    self.assertTrue((REPO_ROOT / rel).is_file(),
                                    f"{column}={rel!r} is not in the repo")

    # -- the generated tree -------------------------------------------------

    def test_generation_is_clean(self):
        self.assertEqual(self.rc, 0)
        self.assertFalse((self.out / "skipped.txt").exists())
        self.assertTrue((self.out / "trainee.ditaval").is_file())
        self.assertTrue((self.out / "instructor.ditaval").is_file())

    def test_main_ditamap_top_level_shape(self):
        """Oxygen renders every direct child of the map as a nav tab and a
        welcome tile, so the top level must be the static pages plus one entry
        per week — never the grams themselves (feature 010)."""
        root = ET.parse(self.out / "main" / "main.ditamap").getroot()
        self.assertEqual(
            [t.get("href") for t in root.findall("topicref")],
            ["welcome.dita", "security.dita", "7_questions.dita",
             "week-1/week_1.dita", "week-2/week_2.dita"],
        )
        self.assertEqual(len(root.findall(".//topicref")), 5)

    def test_progress_test_ditamap_demotes_its_grams(self):
        root = ET.parse(
            self.out / "progress-test-1" / "progress-test-1.ditamap").getroot()
        self.assertEqual(
            [t.get("href") for t in root.findall("topicref")],
            ["welcome.dita", "security.dita", "7_questions.dita", "grams.dita"],
        )

    def test_week_topics_list_their_grams_in_order(self):
        for week in ("week-1", "week-2"):
            topic = self.out / "main" / week / f"{week.replace('-', '_')}.dita"
            root = ET.parse(topic).getroot()
            index = root.find("./body/ul[@outputclass='gram-index']")
            self.assertIsNotNone(index, f"{week} has no gram index")
            self.assertEqual(
                [x.get("href") for x in index.iter("xref")],
                ["gram-01/gram_01.dita", "gram-02/gram_02.dita",
                 "gram-03/gram_03.dita"],
                f"{week} gram index is wrong",
            )

    def test_stretch_page_has_two_demons_then_five_lofars(self):
        """The whole point of the sample: one page that stretches the template
        harder than any gram in the real corpus does (the corpus tops out at
        four Lofars and never pairs them with two demons)."""
        gram = self.out / "main" / "week-1" / "gram-02"
        sections = _sections(gram / "gram_02.dita")
        demons = [s for s in sections if s[0] == "demon-stage"]
        lofars = [s for s in sections if s[0] == "lofar-stage"]
        self.assertEqual([(s[1], s[2]) for s in demons],
                         [("demon", "Demon"), ("demon-2", "Demon 2")])
        self.assertEqual(
            [(s[1], s[2]) for s in lofars],
            [(f"lofar-{n}", f"Lofar {n}") for n in range(1, 6)])
        self.assertEqual([s for s in sections if s[0] == "wav-stage"], [])
        # Demons lead the Lofars on the page.
        self.assertLess(sections.index(demons[-1]), sections.index(lofars[0]))
        # Five *distinct* spectrograms — a slugified-name collision would have
        # silently overwritten one copy and left two sections sharing an image.
        self.assertEqual(
            sorted(p.name for p in gram.glob("lofar-*.png")),
            ["lofar-1.png", "lofar-2-a.png", "lofar-3-abc.png",
             "lofar-3-loop-2.png", "lofar-4-i.png"])
        self.assertTrue((gram / "demon.png").is_file())
        self.assertTrue((gram / "demon-2.png").is_file())

    def test_demons_render_at_the_fixed_band_and_are_unfiltered(self):
        """The demon band is the fixed 0 – 40 Hz, and demons carry no audience
        restriction — in the student editions they lead the page."""
        root = ET.parse(
            self.out / "main" / "week-1" / "gram-02" / "gram_02.dita").getroot()
        demons = [s for s in root.iter("section")
                  if s.get("outputclass") == "demon-stage"]
        self.assertEqual(len(demons), 2)
        for demon, image in zip(demons, ("demon.png", "demon-2.png")):
            self.assertIsNone(demon.get("audience"))
            rows = demon.findall(".//row")
            config = {r.findtext("entry"): r.findall("entry")[-1].text
                      for r in rows if len(r.findall("entry")) == 2}
            self.assertEqual(config, {"time-start": "0", "time-end": "232",
                                      "freq-start": "0", "freq-end": "40"})
            self.assertEqual([i.get("href") for i in demon.iter("image")], [image])

    def test_wav_page_numbers_lofar_and_wav_independently(self):
        """An audio link resolves to no spectrogram, so it must not take a
        number off the Lofar counter (it would promise a gram it cannot show)."""
        gram = self.out / "main" / "week-1" / "gram-03"
        sections = [s for s in _sections(gram / "gram_03.dita")
                    if s[0] in ("lofar-stage", "wav-stage")]
        self.assertEqual(sections, [
            ("lofar-stage", "lofar-1", "Lofar 1"),
            ("wav-stage", "wav-1", "WAV 1"),
            ("lofar-stage", "lofar-2", "Lofar 2"),
            ("lofar-stage", "lofar-3", "Lofar 3"),
        ])

    def test_wav_pair_stays_linked_and_publishable(self):
        """Issue #177: the copied .glc is repointed at the sibling the
        generator wrote, and the topic names the audio in an unfiltered
        <data> so DITA-OT/Oxygen carry it into the output."""
        gram = self.out / "main" / "week-1" / "gram-03"
        self.assertTrue((gram / "lofar-2-loop-1.wav").is_file())
        named = ET.parse(gram / "lofar-2-loop-1.glc").getroot().findtext(
            "data_source/filename")
        self.assertEqual(named, "lofar-2-loop-1.wav")
        root = ET.parse(gram / "gram_03.dita").getroot()
        companion = [d for d in root.iter("data")
                     if d.get("name") == "companion-audio"]
        self.assertEqual([d.get("href") for d in companion],
                         ["lofar-2-loop-1.wav"])

    def test_analysis_word_original_is_copied_but_unreferenced(self):
        """Feature 013: the .docx is parked beside the topic for the analyst
        who has to correct the sheet, and nothing links it — so published
        output is byte-identical whether it is there or not."""
        gram = self.out / "main" / "week-1" / "gram-01"
        self.assertTrue((gram / "analysis.docx").is_file())
        topic = gram / "gram_01.dita"
        self.assertNotIn("analysis.docx", topic.read_text(encoding="utf-8"))
        analysis = [s for s in ET.parse(topic).getroot().iter("section")
                    if s.get("outputclass") == "analysis-sheet"]
        self.assertEqual([s.get("audience") for s in analysis], ["-trainee"])

    def test_weeks_are_renumbered_contiguously(self):
        """``--main-numbering per-week`` renumbers each week 1..k, so a week
        never reads as having missing grams (issue #102). Week 1's source gram
        13 lands at gram-03; no folder keeps a native number."""
        for week in ("week-1", "week-2"):
            folders = sorted(p.name for p in (self.out / "main" / week).iterdir()
                             if p.is_dir())
            self.assertEqual(folders, ["gram-01", "gram-02", "gram-03"])
        root = ET.parse(
            self.out / "main" / "week-1" / "gram-03" / "gram_03.dita").getroot()
        self.assertEqual(root.get("id"), "gram_03")

    def test_progress_test_keeps_its_native_numbering(self):
        """Only ``main`` is renumbered per week; the flat publications keep the
        gram numbers the deck used."""
        folders = sorted(p.name for p in (self.out / "progress-test-1").iterdir()
                         if p.is_dir() and p.name.startswith("gram-"))
        self.assertEqual(folders, ["gram-01", "gram-10", "gram-11"])

    def test_every_href_resolves_within_its_publication(self):
        """The self-contained-publication invariant: open a publication folder
        in Oxygen and publish, with no path rewriting.

        Every per-gram asset is copied beside its topic, so its href is a bare
        filename. The single shared asset is the 7 Questions image, which lives
        once at the publication root and is reached with ``../`` — that one is
        allowed; any other traversal means an asset was not copied.
        """
        for topic in self.out.rglob("*.dita"):
            for element in ET.parse(topic).getroot().iter():
                href = element.get("href")
                if not href or href.startswith(("http:", "https:", "mailto:")):
                    continue
                target = href.split("#", 1)[0]
                if not target:
                    continue
                if ".." in target:
                    self.assertRegex(target, r"^(\.\./)+7_questions\.png$",
                                     f"{topic}: {href} traverses out of its folder")
                resolved = (topic.parent / target).resolve()
                self.assertTrue(resolved.is_file(),
                                f"{topic}: {href} does not resolve")
                self.assertTrue(resolved.is_relative_to(self.out.resolve()),
                                f"{topic}: {href} escapes the DITA tree")

    # -- the committed snapshot --------------------------------------------

    def test_committed_tree_matches_a_fresh_run(self):
        """The committed tree is exactly what the CSV produces today.

        This is the guard that makes committing generated output safe: any
        change to the generator's XML shape, or an edited ``sample.csv``, shows
        up here instead of silently invalidating the snapshot the Oxygen
        template work is tuned against.
        """
        fresh, committed = _files(self.out), _files(COMMITTED_DITA)
        self.assertEqual(
            sorted(fresh - committed), [],
            f"files a fresh run adds — re-run `{REGENERATE}` and commit")
        self.assertEqual(
            sorted(committed - fresh), [],
            f"files a fresh run drops — re-run `{REGENERATE}` and commit")
        differing = [rel for rel in sorted(fresh & committed)
                     if not filecmp.cmp(self.out / rel, COMMITTED_DITA / rel,
                                        shallow=False)]
        self.assertEqual(
            differing, [],
            f"committed content is stale — re-run `{REGENERATE}` and commit")

    def test_regenerate_wrapper_matches_this_harness(self):
        """``regenerate.py`` is the documented entry point; if its flags drift
        from ``setUpClass`` the snapshot test would compare the wrong thing."""
        source = (SAMPLE / "regenerate.py").read_text(encoding="utf-8")
        for flag in ("--csv", "--out", "--image-root", "--static-root",
                     "--seven-questions"):
            self.assertIn(f'"{flag}"', source)
        self.assertNotIn("--stub-wav", source.split('sys.argv = [', 1)[1])


if __name__ == "__main__":
    unittest.main()
