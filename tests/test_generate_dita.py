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

    def test_glc_topic_structure(self) -> None:
        rc = _run(self.out)
        self.assertEqual(rc, 0)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12_lofar1.dita"
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

    def test_glc_topic_asset_copied_with_relative_href(self) -> None:
        """When the referenced asset exists, the generator copies it next to
        the topic (with a slugified filename, preserving the extension) and
        emits a topic-relative href."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12_lofar1.dita"
        copied = gram_dir / "gram12.png"
        original = FIXTURES / "images" / "gram12.png"
        self.assertTrue(copied.is_file(), "asset must be copied next to topic")
        self.assertEqual(copied.read_bytes(), original.read_bytes())
        root = ET.parse(topic).getroot()
        image = root.find(".//image")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("href"), "gram12.png",
                         "href must be topic-relative, not an outward path")

    def test_analysis_topic_asset_copied(self) -> None:
        """Analysis assets are copied into the same per-gram folder as the topic."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12_analysis.dita"
        copied = gram_dir / "gram12-analysis.png"
        self.assertTrue(copied.is_file(), "analysis asset must be copied next to topic")
        root = ET.parse(topic).getroot()
        image = root.find(".//image")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("href"), "gram12-analysis.png")

    def test_analysis_topic_audience_attribute(self) -> None:
        _run(self.out)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12_analysis.dita"
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        self.assertEqual(root.get("audience"), "-trainee")

    def test_main_ditamap_uses_topichead(self) -> None:
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

    def test_test_ditamap_is_flat(self) -> None:
        _run(self.out)
        ditamap = self.out / "progress-test-1.ditamap"
        self.assertTrue(ditamap.is_file())
        root = ET.parse(ditamap).getroot()
        for child in root:
            self.assertEqual(child.tag, "topicref",
                             f"unexpected child {child.tag} in flat test ditamap")
        self.assertIsNone(root.find("topichead"))

    def test_wav_gaps_lite_stub(self) -> None:
        _run(self.out)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05_lofar1.dita"
        self.assertTrue(topic.is_file())
        text = topic.read_text(encoding="utf-8")
        self.assertIn("MANUAL REVIEW", text)
        root = ET.parse(topic).getroot()
        self.assertIsNotNone(root.find(".//note"))
        xref = root.find(".//xref")
        self.assertIsNotNone(xref)
        # The generator copies the WAV next to the topic, renamed to a
        # slugified version of the source filename. The fixture WAV does
        # not exist on disk, so no file is copied, but the href still
        # reflects the intended local name so re-running with the asset
        # present resolves the link without touching the topic XML.
        self.assertEqual(xref.get("href"), "audio-clip.wav")
        self.assertEqual(xref.text, "Audio sample")

    def test_skipped_report_emitted_for_tbd_wav(self) -> None:
        # Build a CSV with a TBD WAV row.
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [
            {c: "" for c in cols},
        ]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 05", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_05_lofar1.dita",
            "display_text": "Audio sample",
            "link_href": "supporting/gram05/audio_clip.wav",
            "wav_treatment": "TBD",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05_lofar1.dita"
        self.assertFalse(topic.exists(), "TBD WAV row must not produce a topic")
        skipped = self.out / "skipped.txt"
        self.assertTrue(skipped.is_file())
        self.assertIn("Gram 05", skipped.read_text(encoding="utf-8"))

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
