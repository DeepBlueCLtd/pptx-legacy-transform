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
            for child in th:
                self.assertEqual(child.tag, "topicref")

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
        for child in root:
            self.assertEqual(child.tag, "topicref",
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
        self.assertIn("Gram 05", skipped.read_text(encoding="utf-8"))

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
        (.png/.jpg/.jpeg) nor .wav — including plausible-looking ones
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
        self.assertIn("Gram 08", skipped)
        self.assertIn(".bmp", skipped,
                      "the skip reason should name the rejected extension")

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


if __name__ == "__main__":
    unittest.main()
