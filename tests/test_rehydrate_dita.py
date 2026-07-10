"""Tests for rehydrate_dita.py (feature 006, User Story 2).

Verifies the inverse transform restores a redirected lofar to a
never-deduplicated form: image and audio-pair round-trips match a baseline
export byte-for-byte (SC-004), un-redirected lofars are untouched, and
--dry-run / missing-master behave per contract.
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

import generate_dita  # noqa: E402
import rehydrate_dita  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures"
TMP = REPO_ROOT / "tests" / "_tmp"

DEDUP_COLUMNS = generate_dita.CSV_COLUMNS + ("master_png_path",)


def _assert_tree_identical(test: unittest.TestCase, a: Path, b: Path) -> None:
    cmp = filecmp.dircmp(a, b)
    test.assertEqual(cmp.diff_files, [], f"differing files under {a} vs {b}")
    test.assertEqual(cmp.left_only, [], f"only in {a}: {cmp.left_only}")
    test.assertEqual(cmp.right_only, [], f"only in {b}: {cmp.right_only}")
    for sub in cmp.common_dirs:
        _assert_tree_identical(test, a / sub, b / sub)


class RehydrateDitaTests(unittest.TestCase):

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = TMP / f"rehy_{self._testMethodName}"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _write_csv(self, name: str, rows: list[dict], with_master: bool) -> Path:
        cols = DEDUP_COLUMNS if with_master else generate_dita.CSV_COLUMNS
        path = self.tmp / name
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})
        return path

    def _generate(self, csv_path: Path, out_name: str) -> Path:
        out = self.tmp / out_name
        rc = generate_dita.main([
            "--csv", str(csv_path), "--out", str(out), "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        return out

    # --- scenario builders -------------------------------------------------
    def _image_rows(self, with_master: bool) -> list[dict]:
        def row(gid, vessel, png, master=""):
            return {
                "publication": "main", "chapter": "Images", "gram_id": gid,
                "vessel_name": vessel, "topic_type": "glc", "sequence": "1",
                "topic_filename": f"gram_{gid}.dita", "display_text": "Image",
                "time_end": "271", "bandwidth": "400", "bandcentre": "200", "png_path": png,
                "master_png_path": master,
            }
        return [
            row("30", "Delta", "dedup/img/shared.png"),
            row("31", "Echo", "dedup/img/shared_b.png",
                "dedup/img/shared.png" if with_master else ""),
        ]

    def _audio_rows(self, with_master: bool) -> list[dict]:
        def row(gid, vessel, wav, glc, master=""):
            return {
                "publication": "main", "chapter": "Audio", "gram_id": gid,
                "vessel_name": vessel, "topic_type": "glc", "sequence": "1",
                "topic_filename": f"gram_{gid}.dita", "display_text": "Audio",
                "link_href": glc, "glc_path": glc, "png_path": wav,
                "time_end": "271", "bandwidth": "400", "bandcentre": "200",
                "master_png_path": master,
            }
        return [
            row("20", "Alpha", "dedup/pair/g20/lofar.wav", "dedup/pair/g20/lofar.glc"),
            row("21", "Bravo", "dedup/pair/g21/lofar.wav", "dedup/pair/g21/lofar.glc",
                "dedup/pair/g20/lofar.wav" if with_master else ""),
        ]

    # -- T020: restored image topic matches baseline ------------------------
    def test_restored_image_topic_matches_baseline(self) -> None:
        baseline = self._generate(
            self._write_csv("base.csv", self._image_rows(False), False), "baseline")
        dedup = self._generate(
            self._write_csv("dd.csv", self._image_rows(True), True), "dedup")
        # Sanity: dedup differs before rehydration (redirected, has <data>).
        self.assertFalse(filecmp.dircmp(baseline, dedup).diff_files == [] and
                         not filecmp.dircmp(baseline, dedup).right_only,
                         "dedup tree should differ from baseline pre-rehydration")
        rc = rehydrate_dita.main(["--dita", str(dedup), "--gram", "gram-31"])
        self.assertEqual(rc, 0)
        # The restored gram-31 now matches the baseline gram-31 exactly.
        _assert_tree_identical(
            self,
            baseline / "main" / "images" / "gram-31",
            dedup / "main" / "images" / "gram-31",
        )

    # -- T021: restored audio pair matches baseline -------------------------
    def test_restored_audio_pair_matches_baseline(self) -> None:
        baseline = self._generate(
            self._write_csv("base.csv", self._audio_rows(False), False), "baseline")
        dedup = self._generate(
            self._write_csv("dd.csv", self._audio_rows(True), True), "dedup")
        g21 = dedup / "main" / "audio" / "gram-21"
        # Pre-rehydration: pair not present locally, <data> present.
        self.assertEqual([p.name for p in g21.iterdir()], ["gram_21.dita"])
        rc = rehydrate_dita.main(["--dita", str(dedup), "--gram", "gram-21"])
        self.assertEqual(rc, 0)
        # Both .glc and .wav restored, topic matches baseline.
        self.assertTrue((g21 / "lofar.glc").is_file())
        self.assertTrue((g21 / "lofar.wav").is_file())
        _assert_tree_identical(
            self, baseline / "main" / "audio" / "gram-21", g21)
        # <data> element is gone.
        root = ET.parse(g21 / "gram_21.dita").getroot()
        self.assertIsNone(root.find(f".//data[@name='{generate_dita.ORIGINAL_ASSET_PATH}']"))

    # -- T022: no-op on un-redirected lofar + idempotent --------------------
    def test_noop_on_unredirected_lofar(self) -> None:
        baseline = self._generate(
            self._write_csv("base.csv", self._image_rows(False), False), "baseline")
        snapshot = self.tmp / "snapshot"
        shutil.copytree(baseline, snapshot)
        # Rehydrating a tree with no <data> changes nothing.
        rc = rehydrate_dita.main(["--dita", str(baseline)])
        self.assertEqual(rc, 0)
        _assert_tree_identical(self, snapshot, baseline)

    def test_second_run_is_noop(self) -> None:
        dedup = self._generate(
            self._write_csv("dd.csv", self._image_rows(True), True), "dedup")
        rehydrate_dita.main(["--dita", str(dedup)])
        after_first = self.tmp / "after_first"
        shutil.copytree(dedup, after_first)
        rehydrate_dita.main(["--dita", str(dedup)])  # second run
        _assert_tree_identical(self, after_first, dedup)

    # -- T023: dry-run writes nothing; missing master warns + relocalises ---
    def test_dry_run_writes_nothing(self) -> None:
        dedup = self._generate(
            self._write_csv("dd.csv", self._image_rows(True), True), "dedup")
        snapshot = self.tmp / "snapshot"
        shutil.copytree(dedup, snapshot)
        rc = rehydrate_dita.main(["--dita", str(dedup), "--dry-run"])
        self.assertEqual(rc, 0)
        _assert_tree_identical(self, snapshot, dedup)

    def test_missing_master_warns_but_relocalises(self) -> None:
        # Generate a redirected tree, then delete the master asset before rehydrating.
        dedup = self._generate(
            self._write_csv("dd.csv", self._image_rows(True), True), "dedup")
        (dedup / "main" / "images" / "gram-30" / "shared.png").unlink()
        rc = rehydrate_dita.main(["--dita", str(dedup), "--gram", "gram-31"])
        self.assertEqual(rc, 0)
        g31 = dedup / "main" / "images" / "gram-31"
        topic = ET.parse(g31 / "gram_31.dita").getroot()
        # Find the gramframe image (not the 7 Questions section image).
        image = topic.find(".//table[@outputclass='gram-config']//image")
        # Href is re-localised even though the copy dangled (drop-in resolves it).
        self.assertEqual(image.get("href"), "shared-b.png")
        self.assertIsNone(topic.find(f".//data[@name='{generate_dita.ORIGINAL_ASSET_PATH}']"))
        log = Path("rehydrate.log").read_text(encoding="utf-8")
        self.assertIn("Master file missing", log)


if __name__ == "__main__":
    unittest.main()
