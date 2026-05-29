"""Tests for generate_dita.py (User Story 1)."""

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

import generate_dita  # noqa: E402
import deduplicate_csv  # noqa: E402


FIXTURES = REPO_ROOT / "tests" / "fixtures"
TMP = REPO_ROOT / "tests" / "_tmp"


def _run(out_dir: Path, csv_path: Path = FIXTURES / "minimal.csv",
         image_root: Path = FIXTURES, clean: bool = True) -> int:
    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    return generate_dita.main([
        "--csv", str(csv_path),
        "--out", str(out_dir),
        "--image-root", str(image_root),
    ])


class GenerateDitaTests(unittest.TestCase):

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.out = TMP / f"out_{self._testMethodName}"
        if self.out.exists():
            shutil.rmtree(self.out)

    def test_gram_topic_has_gramframe_table(self) -> None:
        """Each GLC row contributes one ``<table outputclass='gram-config'>``
        carrying the time/freq parameters the GramFrame plugin reads."""
        rc = _run(self.out)
        self.assertEqual(rc, 0)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        self.assertTrue(topic.is_file(), f"missing {topic}")
        root = ET.parse(topic).getroot()
        self.assertEqual(root.tag, "topic")
        table = root.find(".//table[@outputclass='gram-config']")
        self.assertIsNotNone(table)
        rows = {r.find("entry").text: r.findall("entry")[1].text
                for r in table.findall(".//tbody/row")
                if len(r.findall("entry")) == 2}
        self.assertEqual(rows.get("time-end"), "271")
        self.assertEqual(rows.get("freq-end"), "400")
        ph = root.find("./title/ph[@audience='-trainee']")
        self.assertIsNotNone(ph, "vessel name should be wrapped in <ph audience='-trainee'>")
        self.assertIn("Nordik Jockey", (ph.text or ""))
        # Operator Console v2 theme targets ``span.ph.vessel-name`` in the
        # rendered HTML, which DITA-OT only emits when the source ``<ph>``
        # carries ``outputclass="vessel-name"``.
        self.assertEqual(ph.get("outputclass"), "vessel-name")

    def test_gram_section_outputclasses_match_dark_theme_selectors(self) -> None:
        """The Operator Console v2 theme styles ``section.analysis-sheet`` and
        ``section.lofar-stage``. DITA-OT only emits those class tokens when
        the source ``<section>`` carries the matching ``outputclass``."""
        rc = _run(self.out)
        self.assertEqual(rc, 0)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()

        analysis = root.find(".//section[@audience='-trainee']")
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.get("outputclass"), "analysis-sheet")

        stages = [
            s for s in root.findall(".//section")
            if s.get("outputclass") == "lofar-stage"
        ]
        self.assertGreaterEqual(
            len(stages), 1,
            "expected at least one gram-stage section with outputclass='lofar-stage'",
        )

    def test_glc_section_carries_display_text_title(self) -> None:
        """Each GLC section in a gram topic carries a ``<title>`` set to the
        PPTX link label (``display_text``) so multi-gram pages render a
        clear heading per spectrogram. The minimal fixture's Gram 12 row
        has ``display_text="LOFAR 1"``."""
        _run(self.out)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        section = root.find(".//body/section[table]")
        self.assertIsNotNone(section, "expected a section wrapping the gramframe table")
        title = section.find("title")
        self.assertIsNotNone(title,
                             "GLC section must carry a <title> taken from display_text")
        self.assertEqual(title.text, "LOFAR 1")

    def test_glc_section_omits_title_when_display_text_blank(self) -> None:
        """When ``display_text`` is empty, the section emits no ``<title>``
        — we don't want a blank heading polluting the page."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Nordic Fishing Vessels",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_12.dita",
            "link_href": "supporting/gram12/config_1.glc",
            "glc_path": "supporting/gram12/config_1.glc",
            "time_end": "271", "freq_end": "400",
            "png_path": "images/gram12.png",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        section = root.find(".//body/section[table]")
        self.assertIsNotNone(section)
        self.assertIsNone(section.find("title"),
                          "section must not emit an empty <title>")

    def test_wav_glc_section_carries_display_text_title(self) -> None:
        """The §1.3 GLC-viewer-link section also carries the display_text
        as its ``<title>`` (in addition to the xref's link text), so the
        section heading identifies the link on multi-gram pages."""
        _run(self.out)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05.dita"
        root = ET.parse(topic).getroot()
        xref_section = next(
            (s for s in root.findall(".//body/section") if s.find("p/xref") is not None),
            None,
        )
        self.assertIsNotNone(xref_section,
                             "expected a section wrapping the GLC-viewer xref")
        title = xref_section.find("title")
        self.assertIsNotNone(title,
                             "WAV-typed GLC section must carry a <title> from display_text")
        self.assertEqual(title.text, "Audio sample")

    def test_gramframe_table_has_named_colspecs(self) -> None:
        """DITA-OT needs named colspecs so the image cell renders with
        ``colspan='2'``; without them GramFrame rejects the table."""
        _run(self.out)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        colspecs = root.findall(".//table[@outputclass='gram-config']/tgroup/colspec")
        self.assertEqual([c.get("colname") for c in colspecs], ["c1", "c2"])

    def test_glc_asset_copied_with_slugified_name(self) -> None:
        """When the referenced asset exists, the generator copies it next to
        the topic (with a slugified filename, preserving the extension) and
        emits a topic-relative href."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12.dita"
        copied = gram_dir / "gram12.png"
        original = FIXTURES / "images" / "gram12.png"
        self.assertTrue(copied.is_file(), "asset must be copied next to topic")
        self.assertEqual(copied.read_bytes(), original.read_bytes())
        root = ET.parse(topic).getroot()
        image = root.find(".//table[@outputclass='gram-config']//image")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("href"), "gram12.png",
                         "href must be topic-relative, not an outward path")

    def test_image_present_in_generated_dita(self) -> None:
        """Regression guard: the gramframe block must carry an <image> element
        with a non-empty href pointing at a file that actually exists next to
        the topic. Without this, the published HTML would render an empty
        gram cell — the failure mode that motivated this test."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12.dita"
        root = ET.parse(topic).getroot()
        images = root.findall(".//image")
        self.assertGreaterEqual(len(images), 1,
                                "generated DITA must contain at least one <image>")
        for img in images:
            href = img.get("href")
            self.assertTrue(href, f"<image> is missing href: {ET.tostring(img)!r}")
            self.assertFalse(href.startswith(("/", "..")),
                             f"image href must be topic-relative, got {href!r}")
            self.assertTrue((gram_dir / href).is_file(),
                            f"image file referenced by DITA is missing: {gram_dir / href}")

    def test_analysis_section_in_gram_topic(self) -> None:
        """Analysis assets are copied into the per-gram folder and the gram
        topic carries an instructor-only analysis section (PNG embedded as
        <image>, DOCX linked via <xref>)."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12.dita"
        copied = gram_dir / "gram12-analysis.png"
        self.assertTrue(copied.is_file(), "analysis asset must be copied next to topic")
        root = ET.parse(topic).getroot()
        analysis_section = root.find(".//body/section[@audience='-trainee']")
        self.assertIsNotNone(analysis_section,
                             "gram topic must include an instructor-only analysis section")
        image = analysis_section.find("image")
        self.assertIsNotNone(image, "PNG analysis assets render as <image>")
        self.assertEqual(image.get("href"), "gram12-analysis.png")

    def test_docx_analysis_renders_as_xref(self) -> None:
        """When the analysis asset is a .docx, the section emits an <xref>
        instead of an embedded <image>."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [
            {c: "" for c in cols},
            {c: "" for c in cols},
        ]
        rows[0].update({
            "publication": "main", "chapter": "Nordic Fishing Vessels",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_12.dita",
            "link_href": "supporting/gram12/config_1.glc",
            "glc_path": "supporting/gram12/config_1.glc",
            "time_end": "271", "freq_end": "400",
            "png_path": "images/gram12.png",
        })
        rows[1].update({
            "publication": "main", "chapter": "Nordic Fishing Vessels",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "analysis", "sequence": "1",
            "topic_filename": "gram_12.dita",
            "png_path": "analysis.docx",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        analysis_section = root.find(".//body/section[@audience='-trainee']")
        self.assertIsNotNone(analysis_section)
        xref = analysis_section.find(".//xref")
        self.assertIsNotNone(xref, "DOCX analysis assets render as <xref>")
        self.assertEqual(xref.get("href"), "analysis.docx")
        self.assertEqual(xref.get("format"), "docx")

    def test_main_ditamap_topichead_per_chapter(self) -> None:
        _run(self.out)
        ditamap = self.out / "main.ditamap"
        self.assertTrue(ditamap.is_file())
        root = ET.parse(ditamap).getroot()
        self.assertEqual(root.tag, "map")
        topicheads = root.findall("topichead")
        self.assertGreaterEqual(len(topicheads), 1)
        for th in topicheads:
            # Spec 003: chapter navtitles live inside <topicmeta>/<navtitle>
            # (replaces the legacy navtitle= attribute). Each chapter's
            # children are exactly one <topicmeta> followed by one or more
            # <topicref> elements — no nested <topichead>.
            for child in th:
                self.assertIn(child.tag, {"topicmeta", "topicref"})
            self.assertIsNone(th.find("topichead"),
                              "no nested topicheads — chapter layout is one level deep")

    def test_main_ditamap_one_topicref_per_gram(self) -> None:
        """The CSV carries N+1 rows per gram but the ditamap must point to
        the single gram topic once, not once per row."""
        _run(self.out)
        ditamap = self.out / "main.ditamap"
        root = ET.parse(ditamap).getroot()
        hrefs = [tr.get("href") for tr in root.findall(".//topicref")]
        self.assertEqual(len(hrefs), len(set(hrefs)),
                         f"duplicate topicrefs in ditamap: {hrefs}")

    def test_test_ditamap_is_flat(self) -> None:
        _run(self.out)
        ditamap = self.out / "progress-test-1.ditamap"
        self.assertTrue(ditamap.is_file())
        root = ET.parse(ditamap).getroot()
        # Spec 003: every ditamap carries a <title> child element (replaces
        # the legacy title= attribute). Flat = no <topichead> below the
        # title. Children are <title> followed by <topicref> elements.
        for child in root:
            self.assertIn(child.tag, {"title", "topicref"},
                          f"unexpected child {child.tag} in flat test ditamap")
        self.assertIsNone(root.find("topichead"))

    def test_glc_inner_wav_renders_as_glc_viewer_link(self) -> None:
        """A GLC row whose inner asset is a .wav renders as a §1.3
        GLC-viewer-link block: a plain <xref> to the .glc (so the
        on-PC GLC viewer opens it and resolves the .wav next to it),
        with no <image> and no gramframe table for that row."""
        _run(self.out)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05.dita"
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        # No gramframe table for this row (no pre-rendered spectrogram).
        self.assertIsNone(root.find(".//table[@outputclass='gram-config']"))
        # No <image> either — the WAV is not a renderable image.
        self.assertIsNone(root.find(".//image"))
        xref = root.find(".//xref")
        self.assertIsNotNone(xref, "WAV-typed GLC row must emit an <xref>")
        # The href targets the .glc (slugified), not the .wav: the GLC
        # viewer reads the .glc's <filename> element to find the audio.
        self.assertEqual(xref.get("href"), "config.glc")
        self.assertEqual(xref.get("format"), "glc")
        self.assertEqual(xref.get("scope"), "local")
        self.assertEqual(xref.text, "Audio sample")

    def test_glc_row_without_classifiable_asset_is_skipped(self) -> None:
        """A GLC row whose png_path is empty (or carries an extension
        the generator cannot dispatch on) contributes no block to its
        gram topic and is recorded in skipped.txt."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [
            {c: "" for c in cols},
        ]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 05", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_05.dita",
            "display_text": "Audio sample",
            "link_href": "supporting/gram05/config.glc",
            "glc_path": "supporting/gram05/config.glc",
            # png_path left empty — the .glc parse failed to yield an
            # inner asset filename, so there's nothing to dispatch on.
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05.dita"
        # The skipped row contributes no block, but the gram topic still
        # renders (empty body bar the title).
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        self.assertIsNone(root.find(".//table[@outputclass='gram-config']"))
        skipped = self.out / "skipped.txt"
        self.assertTrue(skipped.is_file())
        self.assertIn('gram_id="5"', skipped.read_text(encoding="utf-8"))

    def test_glc_inner_wav_copies_glc_and_wav_pair(self) -> None:
        """End-to-end happy path for the §1.3 GLC-viewer-link contract:
        when both the .glc and the named .wav exist on disk, the
        generator copies both into the per-gram folder under slugified
        names, byte-identical to the source, so the on-PC GLC viewer
        can resolve the audio. Covers the success branches that
        ``test_glc_inner_wav_renders_as_glc_viewer_link`` skips
        (fixture .glc/.wav are missing there, so the copy is a no-op)."""
        glc_src = TMP / "wav_pair_src" / "supporting" / "gram07" / "config.glc"
        wav_src = TMP / "wav_pair_src" / "supporting" / "gram07" / "audio_clip.wav"
        glc_src.parent.mkdir(parents=True, exist_ok=True)
        glc_src.write_bytes(b"<GAPS_Lite_configuration/>")
        wav_src.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 07", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_07.dita",
            "display_text": "Lofar 1",
            "link_href": "supporting/gram07/config.glc",
            "glc_path": "supporting/gram07/config.glc",
            "png_path": "supporting/gram07/audio_clip.wav",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path, image_root=TMP / "wav_pair_src")
        gram_dir = self.out / "main" / "arctic-survey" / "gram-07"
        glc_copy = gram_dir / "config.glc"
        wav_copy = gram_dir / "audio-clip.wav"
        self.assertTrue(glc_copy.is_file(), "the .glc must be copied next to the topic")
        self.assertTrue(wav_copy.is_file(),
                        "the companion .wav must travel with the .glc so the "
                        "on-PC viewer can resolve it")
        self.assertEqual(glc_copy.read_bytes(), glc_src.read_bytes())
        self.assertEqual(wav_copy.read_bytes(), wav_src.read_bytes())
        # And the topic's xref must point at the slugified .glc.
        topic = gram_dir / "gram_07.dita"
        root = ET.parse(topic).getroot()
        xref = root.find(".//xref")
        self.assertIsNotNone(xref)
        self.assertEqual(xref.get("href"), "config.glc")
        self.assertEqual(xref.get("format"), "glc")

    def test_glc_row_with_unsupported_extension_is_skipped(self) -> None:
        """The dispatch must reject any extension that is neither image
        (.png/.jpg/.jpeg/.gif) nor .wav — including plausible-looking ones
        like .bmp or .pdf — and record the skip with the offending
        extension in the reason so the technical author can triage."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 08", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_08.dita",
            "display_text": "Lofar 1",
            "link_href": "supporting/gram08/config.glc",
            "glc_path": "supporting/gram08/config.glc",
            "png_path": "supporting/gram08/spectrogram.bmp",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "arctic-survey" / "gram-08" / "gram_08.dita"
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        self.assertIsNone(root.find(".//image"))
        self.assertIsNone(root.find(".//xref"))
        skipped = (self.out / "skipped.txt").read_text(encoding="utf-8")
        self.assertIn('gram_id="8"', skipped)
        self.assertIn(".bmp", skipped,
                      "the skip reason should name the rejected extension")

    def test_glc_row_with_gif_asset_embeds_gramframe_image(self) -> None:
        """A pre-rendered spectrogram named in the GLC may be a ``.gif``
        (some legacy decks use them). It must dispatch to the inline
        GramFrame table exactly like ``.png``/``.jpg`` — not be skipped —
        and the case of the source suffix (``.GIF``) must not matter."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 09", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_09.dita",
            "display_text": "Lofar 1",
            "link_href": "supporting/gram09/config.glc",
            "glc_path": "supporting/gram09/config.glc",
            "png_path": "supporting/gram09/spectrogram.GIF",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "arctic-survey" / "gram-09" / "gram_09.dita"
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        image = root.find(".//table[@outputclass='gram-config']//image")
        self.assertIsNotNone(image, "a .gif Lofar must embed a GramFrame image")
        self.assertEqual(image.get("href"), "spectrogram.gif",
                         "the copied asset href is the slugified, lower-cased name")
        skipped = self.out / "skipped.txt"
        if skipped.is_file():
            self.assertNotIn("spectrogram", skipped.read_text(encoding="utf-8"),
                             "a .gif Lofar must not be skipped")

    def test_idempotent_output(self) -> None:
        rc1 = _run(self.out, clean=True)
        self.assertEqual(rc1, 0)
        snapshot = TMP / f"{self._testMethodName}_snapshot"
        if snapshot.exists():
            shutil.rmtree(snapshot)
        shutil.copytree(self.out, snapshot)
        rc2 = _run(self.out, clean=False)
        self.assertEqual(rc2, 0)
        diff = filecmp.dircmp(self.out, snapshot)
        differing = self._collect_diffs(diff)
        self.assertEqual(differing, [], f"non-idempotent files: {differing}")

    def _collect_diffs(self, diff: filecmp.dircmp) -> list[str]:
        result = list(diff.diff_files) + list(diff.left_only) + list(diff.right_only)
        for sub in diff.subdirs.values():
            result.extend(self._collect_diffs(sub))
        return result

    def test_trainee_ditaval_emitted_with_exact_bytes(self) -> None:
        """``publish_html.py`` aborts unless ``<dita>/trainee.ditaval`` exists
        with the audience-exclude rule, so the generator must produce it
        every run — even after ``--clean`` wipes the tree."""
        _run(self.out)
        ditaval = self.out / "trainee.ditaval"
        self.assertTrue(ditaval.is_file(), f"missing {ditaval}")
        self.assertEqual(
            ditaval.read_text(encoding="utf-8"),
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<val>\n'
            '  <prop att="audience" val="-trainee" action="exclude"/>\n'
            '</val>\n',
        )
        manifest_lines = (self.out / "manifest.txt").read_text(encoding="utf-8").splitlines()
        self.assertIn("trainee.ditaval", manifest_lines)

    def test_manifest_lists_every_output_file(self) -> None:
        _run(self.out)
        manifest = self.out / "manifest.txt"
        self.assertTrue(manifest.is_file())
        listed = set(manifest.read_text(encoding="utf-8").splitlines())
        listed.discard("")
        actual = set()
        for path in self.out.rglob("*"):
            if path.is_file() and path.name not in {"manifest.txt", "skipped.txt"}:
                actual.add(path.relative_to(self.out).as_posix())
        self.assertEqual(listed, actual)
        self.assertEqual(sorted(listed), list(manifest.read_text(encoding="utf-8").splitlines()[:len(listed)]),
                         "manifest must be sorted")


class AudienceShapeTests(unittest.TestCase):
    """Spec 003 — chapter slug normalisation and audience-tagged ditamap shape.

    Drives `generate_dita.py` against ``tests/fixtures/audience_minimal.csv``
    which carries one "Instructor "-prefixed chapter, one plain chapter,
    and a mix of vessel-name and no-vessel-name grams.
    """

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.out = TMP / f"out_{self._testMethodName}"
        if self.out.exists():
            shutil.rmtree(self.out)
        rc = _run(self.out, csv_path=FIXTURES / "audience_minimal.csv")
        self.assertEqual(rc, 0)

    def test_chapter_slug_strips_instructor_prefix(self) -> None:
        """Chapter "Instructor Week 1 Grams" → folder ``main/week-1-grams/``
        (no ``instructor-`` prefix anywhere in the source tree)."""
        normalised_chapter = self.out / "main" / "week-1-grams"
        legacy_chapter = self.out / "main" / "instructor-week-1-grams"
        self.assertTrue(normalised_chapter.is_dir(),
                        f"normalised chapter folder missing: {normalised_chapter}")
        self.assertFalse(legacy_chapter.exists(),
                         f"legacy instructor-prefixed folder must not exist: {legacy_chapter}")
        for path in self.out.rglob("*"):
            self.assertNotIn(
                "instructor", path.name.lower(),
                f'no path component under {self.out} may contain "instructor": {path}',
            )

    def test_map_title_uses_title_element_not_attribute(self) -> None:
        """Map title is a ``<title>`` child of ``<map>`` carrying an audience-
        tagged ``<ph audience="-trainee"> — Instructor Version</ph>`` suffix.
        The legacy ``title=`` attribute on ``<map>`` is no longer emitted."""
        ditamap = self.out / "main.ditamap"
        root = ET.parse(ditamap).getroot()
        self.assertIsNone(root.get("title"),
                          'legacy title="..." attribute on <map> must not be emitted')
        title = root.find("title")
        self.assertIsNotNone(title, "<map> must carry a <title> child element")
        self.assertEqual(title.text, "Main",
                         "audience-neutral title text precedes the audience-tagged <ph>")
        ph = title.find("ph[@audience='-trainee']")
        self.assertIsNotNone(ph,
                             '<title> must contain a <ph audience="-trainee"> suffix')
        self.assertEqual(ph.text, " — Instructor Version")
        # The progress-test ditamap follows the same shape.
        pt_ditamap = self.out / "progress-test-1.ditamap"
        pt_root = ET.parse(pt_ditamap).getroot()
        self.assertIsNone(pt_root.get("title"))
        pt_title = pt_root.find("title")
        self.assertIsNotNone(pt_title)
        self.assertEqual(pt_title.text, "Progress Test 1")
        pt_ph = pt_title.find("ph[@audience='-trainee']")
        self.assertIsNotNone(pt_ph)
        self.assertEqual(pt_ph.text, " — Instructor Version")

    def test_topichead_uses_topicmeta_navtitle(self) -> None:
        """Each ``<topichead>`` carries ``<topicmeta>/<navtitle>``. Chapters
        whose source name began with "Instructor " emit the prefix inside
        ``<ph audience="-trainee">`` and the remainder as the navtitle tail.
        The legacy ``navtitle=`` attribute on ``<topichead>`` is no longer
        emitted."""
        ditamap = self.out / "main.ditamap"
        root = ET.parse(ditamap).getroot()
        topicheads = root.findall("topichead")
        self.assertEqual(len(topicheads), 2,
                         "fixture defines two main chapters")
        navtitles_by_kind: dict[str, ET.Element] = {}
        for th in topicheads:
            self.assertIsNone(
                th.get("navtitle"),
                'legacy navtitle="..." attribute on <topichead> must not be emitted',
            )
            topicmeta = th.find("topicmeta")
            self.assertIsNotNone(topicmeta,
                                 "<topichead> must carry a <topicmeta> child")
            navtitle = topicmeta.find("navtitle")
            self.assertIsNotNone(navtitle,
                                 "<topicmeta> must carry a <navtitle> child")
            ph = navtitle.find("ph[@audience='-trainee']")
            kind = "instructor_prefixed" if ph is not None else "plain"
            navtitles_by_kind[kind] = navtitle
        self.assertIn("instructor_prefixed", navtitles_by_kind,
                      "fixture defines an Instructor-prefixed chapter")
        self.assertIn("plain", navtitles_by_kind,
                      "fixture defines a plain chapter")
        prefixed = navtitles_by_kind["instructor_prefixed"]
        prefixed_ph = prefixed.find("ph")
        self.assertEqual(prefixed_ph.text, "Instructor ",
                         "audience-tagged prefix preserves the leading 'Instructor ' word + space")
        self.assertEqual(prefixed_ph.tail, "Week 1 Grams",
                         "remainder text follows the <ph> as its tail")
        plain = navtitles_by_kind["plain"]
        self.assertEqual(plain.text, "Plain Chapter",
                         "plain chapters emit text directly with no <ph> wrapper")
        self.assertEqual(len(list(plain)), 0,
                         "plain navtitle must have no child elements")


class CsvRefactoringSupportTests(unittest.TestCase):
    """Author-side refactoring support at the CSV stage.

    The CSV doubles as the surface where the author redistributes
    grams between chapters/publications (e.g. dissolving a Pub10
    reference chapter). These tests cover the two affordances that
    make that ergonomic and safe: integer-style ``gram_id`` cells and
    pre-emission detection of duplicate row identities.
    """

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = TMP / f"refactor_{self._testMethodName}"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _write_csv(self, rows: list[dict]) -> Path:
        csv_path = self.tmp / "source.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=list(generate_dita.CSV_COLUMNS),
                lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row.get(col, "") for col in generate_dita.CSV_COLUMNS})
        return csv_path

    def test_normalise_gram_id_canonicalises_to_plain_integer(self) -> None:
        self.assertEqual(generate_dita._normalise_gram_id("12"), "12")
        self.assertEqual(generate_dita._normalise_gram_id("5"), "5")
        self.assertEqual(generate_dita._normalise_gram_id(" 7 "), "7")
        self.assertEqual(generate_dita._normalise_gram_id("05"), "5")

    def test_normalise_gram_id_accepts_legacy_forms(self) -> None:
        self.assertEqual(generate_dita._normalise_gram_id("Gram 12"), "12")
        self.assertEqual(generate_dita._normalise_gram_id("gram 5"), "5")
        self.assertEqual(generate_dita._normalise_gram_id("Gram-7"), "7")

    def test_normalise_gram_id_passes_through_when_no_digits(self) -> None:
        self.assertEqual(generate_dita._normalise_gram_id(""), "")
        self.assertEqual(generate_dita._normalise_gram_id("TBD"), "TBD")

    def test_read_csv_normalises_gram_id_column(self) -> None:
        """Mixed integer/legacy forms in the same gram still group as one."""
        csv_path = self._write_csv([
            {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "12",
             "vessel_name": "FR Foo", "topic_type": "glc", "sequence": "1",
             "topic_filename": "gram_12.dita", "display_text": "LOFAR 1",
             "link_href": "supporting/gram12/c.glc",
             "glc_path": "supporting/gram12/c.glc",
             "time_end": "271", "freq_end": "400",
             "png_path": "images/gram12.png"},
            {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "Gram 12",
             "vessel_name": "FR Foo", "topic_type": "analysis", "sequence": "1",
             "topic_filename": "gram_12.dita",
             "png_path": "images/gram12_analysis.png"},
        ])
        rows = generate_dita.read_csv(csv_path)
        self.assertEqual([r["gram_id"] for r in rows], ["12", "12"])

    def test_main_succeeds_with_integer_gram_ids(self) -> None:
        """A CSV authored with bare integers emits to the same paths as
        the legacy ``"Gram NN"`` form would."""
        csv_path = self._write_csv([
            {"publication": "main", "chapter": "Nordic Fishing Vessels",
             "gram_id": "12", "vessel_name": "Nordik Jockey",
             "topic_type": "glc", "sequence": "1", "topic_filename": "gram_12.dita",
             "display_text": "LOFAR 1",
             "link_href": "supporting/gram12/config_1.glc",
             "glc_path": "supporting/gram12/config_1.glc",
             "time_end": "271", "freq_end": "400",
             "png_path": "images/gram12.png"},
            {"publication": "main", "chapter": "Nordic Fishing Vessels",
             "gram_id": "12", "vessel_name": "Nordik Jockey",
             "topic_type": "analysis", "sequence": "1",
             "topic_filename": "gram_12.dita",
             "png_path": "images/gram12_analysis.png"},
        ])
        rc = generate_dita.main([
            "--csv", str(csv_path),
            "--out", str(self.tmp / "out"),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        topic = self.tmp / "out" / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        self.assertTrue(topic.is_file(), f"missing {topic}")

    def test_check_row_identity_flags_two_grams_in_same_slot(self) -> None:
        """Simulates: author moves a Pub10 gram into Week 2 but forgets
        to renumber — Week 2 already had a Gram 05. Both analysis rows
        and both ``glc:sequence=1`` rows collide."""
        rows = [
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "analysis", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "analysis", "sequence": "1"},
        ]
        errors = generate_dita.check_row_identity(rows)
        self.assertEqual(len(errors), 2,
                         f"expected one error per duplicate slot, got {errors}")
        for msg in errors:
            self.assertIn("Gram 05", msg)
            self.assertIn("renumber", msg.lower())

    def test_check_row_identity_clean_on_distinct_rows(self) -> None:
        rows = [
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "2"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "analysis", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 06",
             "topic_type": "analysis", "sequence": "1"},
        ]
        self.assertEqual(generate_dita.check_row_identity(rows), [])

    # The two distinct Week 2 grams that both claim number 5 (feature 008).
    _COLLIDING_GRAMS = [
        # Native Week 2 / Gram 5
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "5",
         "vessel_name": "Vessel A", "topic_type": "glc", "sequence": "1",
         "topic_filename": "gram_05.dita", "display_text": "LOFAR 1",
         "link_href": "supporting/a/c.glc", "glc_path": "supporting/a/c.glc",
         "time_end": "180", "freq_end": "400", "png_path": "images/a.png"},
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "5",
         "vessel_name": "Vessel A", "topic_type": "analysis", "sequence": "1",
         "topic_filename": "gram_05.dita", "png_path": "images/a_an.png"},
        # A Pub10 gram reassigned to Week 2 that also claims number 5.
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "Gram 05",
         "vessel_name": "Vessel B", "topic_type": "glc", "sequence": "1",
         "topic_filename": "gram_05.dita", "display_text": "LOFAR 1",
         "link_href": "supporting/b/c.glc", "glc_path": "supporting/b/c.glc",
         "time_end": "271", "freq_end": "400", "png_path": "images/b.png"},
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "Gram 05",
         "vessel_name": "Vessel B", "topic_type": "analysis", "sequence": "1",
         "topic_filename": "gram_05.dita", "png_path": "images/b_an.png"},
    ]

    def test_main_aborts_on_unrenumbered_collision(self) -> None:
        """Two distinct grams sharing a week + number with no renumbering
        applied must abort the run (the safety net that replaces the old
        letter-suffix auto-disambiguation), not silently merge (feature 008)."""
        csv_path = self._write_csv(self._COLLIDING_GRAMS)
        out_dir = self.tmp / "out"
        rc = generate_dita.main([
            "--csv", str(csv_path),
            "--out", str(out_dir),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 1, "generator must abort on an un-renumbered collision")
        self.assertFalse((out_dir / "main" / "week-2-grams").exists(),
                         "no topic should be written when the run aborts")

    def test_renumbering_resolves_collision_into_unique_folders(self) -> None:
        """Running the dedupe renumber step assigns the later gram a fresh
        number (max+1), so the two grams land at distinct gram-NN folders with
        no letter suffix (feature 008)."""
        rows = [dict(r) for r in self._COLLIDING_GRAMS]
        renumbered = deduplicate_csv.renumber_grams(rows)
        self.assertEqual(renumbered, 1, "exactly the second gram is renumbered")

        cols = list(generate_dita.CSV_COLUMNS) + ["target_gram_id"]
        csv_path = self.tmp / "renumbered.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols,
                                    lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for row in rows:
                writer.writerow({c: row.get(c, "") for c in cols})

        out_dir = self.tmp / "out"
        rc = generate_dita.main([
            "--csv", str(csv_path),
            "--out", str(out_dir),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0, "generator must accept the renumbered CSV")
        chapter_dir = out_dir / "main" / "week-2-grams"
        self.assertTrue((chapter_dir / "gram-05" / "gram_05.dita").is_file(),
                        "native gram keeps number 5")
        self.assertTrue((chapter_dir / "gram-06" / "gram_06.dita").is_file(),
                        "renumbered gram lands at max+1 = 6, no letter suffix")
        self.assertFalse((chapter_dir / "gram-05a").exists(),
                         "letter-suffix folders must no longer be produced")

    def test_bare_integer_target_chapter_expands_to_week(self) -> None:
        """Feature 008: target_chapter="2" lands under main/week-2/ and the
        main ditamap heads the chapter "Week 2"."""
        cols = list(generate_dita.CSV_COLUMNS) + ["target_chapter"]
        csv_path = self.tmp / "weeks.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols,
                                    lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for row in [
                {"publication": "main", "chapter": "Instructor Pub10_Ed22B_Updated",
                 "target_chapter": "2", "gram_id": "7", "vessel_name": "Nordik",
                 "topic_type": "glc", "sequence": "1", "topic_filename": "gram_07.dita",
                 "display_text": "LOFAR 1", "link_href": "supporting/g/c.glc",
                 "glc_path": "supporting/g/c.glc", "time_end": "271", "freq_end": "400",
                 "png_path": "images/g.png"},
                {"publication": "main", "chapter": "Instructor Pub10_Ed22B_Updated",
                 "target_chapter": "2", "gram_id": "7", "vessel_name": "Nordik",
                 "topic_type": "analysis", "sequence": "1", "topic_filename": "gram_07.dita",
                 "png_path": "images/g_an.png"},
            ]:
                writer.writerow({c: row.get(c, "") for c in cols})

        out_dir = self.tmp / "out"
        rc = generate_dita.main([
            "--csv", str(csv_path), "--out", str(out_dir),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        self.assertTrue((out_dir / "main" / "week-2" / "gram-07" / "gram_07.dita").is_file(),
                        "bare-integer chapter must slug to week-2, not pub10")
        ditamap = (out_dir / "main.ditamap").read_text(encoding="utf-8")
        self.assertIn("<navtitle>Week 2</navtitle>", ditamap)
        self.assertIn("main/week-2/gram-07/gram_07.dita", ditamap)


class DedupGenerateDitaTests(unittest.TestCase):
    """Large-asset deduplication redirect behaviour (feature 006, US1).

    These tests hand-craft a CSV carrying the optional ``master_png_path``
    column (as ``deduplicate_csv.py`` would produce) and assert the
    generator redirects to a single master copy, records provenance, stays
    inert when the column is absent, and remains idempotent.
    """

    DEDUP_COLUMNS = generate_dita.CSV_COLUMNS + ("master_png_path",)

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = TMP / f"dedup_{self._testMethodName}"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _write_csv(self, rows: list[dict], cols=None) -> Path:
        cols = cols or self.DEDUP_COLUMNS
        csv_path = self.tmp / "source.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=list(cols),
                lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({c: row.get(c, "") for c in cols})
        return csv_path

    def _generate(self, csv_path: Path, out_name: str = "out") -> Path:
        out_dir = self.tmp / out_name
        rc = generate_dita.main([
            "--csv", str(csv_path), "--out", str(out_dir),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        return out_dir

    def _image_glc_row(self, gid, vessel, png, master="") -> dict:
        return {
            "publication": "main", "chapter": "Images", "gram_id": gid,
            "vessel_name": vessel, "topic_type": "glc", "sequence": "1",
            "topic_filename": f"gram_{gid}.dita", "display_text": "Image",
            "time_end": "271", "freq_end": "400", "png_path": png,
            "master_png_path": master,
        }

    def _audio_glc_row(self, gid, vessel, wav, glc, master="") -> dict:
        return {
            "publication": "main", "chapter": "Audio", "gram_id": gid,
            "vessel_name": vessel, "topic_type": "glc", "sequence": "1",
            "topic_filename": f"gram_{gid}.dita", "display_text": "Audio",
            "link_href": glc, "glc_path": glc, "png_path": wav,
            "master_png_path": master,
        }

    # -- T006: inert when the master_png_path column is absent ---------------
    def test_inert_when_master_column_absent(self) -> None:
        """A CSV without master_png_path produces byte-identical output to a
        baseline run and emits no <data> element anywhere (FR-010, SC-005)."""
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png"),
        ]
        # With column present-but-empty.
        with_col = self._generate(self._write_csv(rows), "with_col")
        # Without the column at all (legacy 16-col CSV).
        csv_no_col = self.tmp / "no_col.csv"
        with csv_no_col.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(generate_dita.CSV_COLUMNS),
                               lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in generate_dita.CSV_COLUMNS})
        without_col = self.tmp / "without_col"
        rc = generate_dita.main([
            "--csv", str(csv_no_col), "--out", str(without_col),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        cmp = filecmp.dircmp(with_col, without_col)
        self.assertEqual(cmp.diff_files, [], "present-empty column must be inert")
        self.assertEqual(cmp.left_only, [])
        self.assertEqual(cmp.right_only, [])
        # No <data> emitted, and both grams copied their own image.
        for topic in without_col.rglob("*.dita"):
            root = ET.parse(topic).getroot()
            self.assertIsNone(root.find(f".//data[@name='{generate_dita.ORIGINAL_ASSET_PATH}']"))
        self.assertTrue((without_col / "main" / "images" / "gram-31" / "shared-b.png").is_file())

    # -- T007: redirected image links the master, copies nothing -------------
    def test_redirected_image_href_points_to_master(self) -> None:
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/shared.png"),
        ]
        out = self._generate(self._write_csv(rows))
        g31 = out / "main" / "images" / "gram-31"
        topic = ET.parse(g31 / "gram_31.dita").getroot()
        image = topic.find(".//table[@outputclass='gram-config']//image")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("href"), "../gram-30/shared.png")
        # No local copy in the redirected gram.
        self.assertFalse((g31 / "shared-b.png").exists())
        self.assertFalse((g31 / "shared.png").exists())
        # Master copy exists in gram-30.
        self.assertTrue((out / "main" / "images" / "gram-30" / "shared.png").is_file())

    # -- T008: redirected audio links the master .glc, pairs untouched -------
    def test_redirected_audio_links_master_glc(self) -> None:
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
        ]
        out = self._generate(self._write_csv(rows))
        g21 = out / "main" / "audio" / "gram-21"
        topic = ET.parse(g21 / "gram_21.dita").getroot()
        xref = topic.find(".//xref[@format='glc']")
        self.assertIsNotNone(xref)
        self.assertEqual(xref.get("href"), "../gram-20/master.glc")
        # Neither .glc nor .wav copied into the redirected gram.
        self.assertEqual(sorted(p.name for p in g21.iterdir()), ["gram_21.dita"])
        # Master gram holds both files side by side.
        g20 = out / "main" / "audio" / "gram-20"
        self.assertTrue((g20 / "master.glc").is_file())
        self.assertTrue((g20 / "master.wav").is_file())

    # -- T009: master binary written exactly once across N redirects --------
    def test_master_binary_written_exactly_once(self) -> None:
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
            self._audio_glc_row("22", "Charlie", "dedup/audio/dup2.wav",
                                "dedup/audio/dup2.glc",
                                master="dedup/audio/master.wav"),
        ]
        out = self._generate(self._write_csv(rows))
        wavs = sorted(p for p in out.rglob("*.wav"))
        self.assertEqual(len(wavs), 1, f"exactly one physical .wav, got {wavs}")
        glcs = sorted(p for p in out.rglob("*.glc"))
        self.assertEqual(len(glcs), 1, f"exactly one physical .glc, got {glcs}")

    # -- T010: provenance <data> on redirected lofars only ------------------
    def test_provenance_data_emitted_on_redirected_lofar_only(self) -> None:
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/shared.png"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
        ]
        out = self._generate(self._write_csv(rows))
        name = generate_dita.ORIGINAL_ASSET_PATH

        def data_values(topic_path):
            root = ET.parse(topic_path).getroot()
            return [d.get("value") for d in root.findall(f".//data[@name='{name}']")]

        # Redirected image gram: value is the row's own png_path.
        self.assertEqual(
            data_values(out / "main" / "images" / "gram-31" / "gram_31.dita"),
            ["dedup/img/shared_b.png"],
        )
        # Redirected audio gram: value is the row's glc_path (not the .wav).
        self.assertEqual(
            data_values(out / "main" / "audio" / "gram-21" / "gram_21.dita"),
            ["dedup/audio/dup1.glc"],
        )
        # Masters carry none.
        self.assertEqual(data_values(out / "main" / "images" / "gram-30" / "gram_30.dita"), [])
        self.assertEqual(data_values(out / "main" / "audio" / "gram-20" / "gram_20.dita"), [])

    # -- T011: blank/unresolvable master falls back with a WARNING ----------
    def test_blank_or_unresolvable_master_falls_back_with_warning(self) -> None:
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            # master_png_path points at a png_path no master row owns.
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/does_not_exist.png"),
        ]
        csv_path = self._write_csv(rows)
        out = self._generate(csv_path)
        # main() reconfigures root logging, so assert against the dual-logged
        # generate.log file (the air-gapped debugging surface) rather than
        # assertLogs (whose handler setup_logging would remove).
        log_text = Path("generate.log").read_text(encoding="utf-8")
        self.assertIn("not resolvable", log_text)
        self.assertIn("dedup/img/does_not_exist.png", log_text)
        g31 = out / "main" / "images" / "gram-31"
        # Fell back to a local copy; no <data> emitted.
        self.assertTrue((g31 / "shared-b.png").is_file())
        topic = ET.parse(g31 / "gram_31.dita").getroot()
        self.assertIsNone(topic.find(f".//data[@name='{generate_dita.ORIGINAL_ASSET_PATH}']"))

    # -- T012: deduplicated export is idempotent ----------------------------
    def test_dedup_export_idempotent(self) -> None:
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/shared.png"),
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
        ]
        csv_path = self._write_csv(rows)
        first = self._generate(csv_path, "run1")
        second = self._generate(csv_path, "run2")

        def _assert_identical(a: Path, b: Path) -> None:
            cmp = filecmp.dircmp(a, b)
            self.assertEqual(cmp.diff_files, [], f"diffs under {a}")
            self.assertEqual(cmp.left_only, [])
            self.assertEqual(cmp.right_only, [])
            for sub in cmp.common_dirs:
                _assert_identical(a / sub, b / sub)

        _assert_identical(first, second)


if __name__ == "__main__":
    unittest.main()
