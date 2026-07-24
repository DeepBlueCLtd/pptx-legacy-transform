"""Tests for the GLC parser (User Story 2)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import extract_to_csv  # noqa: E402


FIXTURES = REPO_ROOT / "tests" / "fixtures"
TMP = REPO_ROOT / "tests" / "_tmp"


class GlcParserTests(unittest.TestCase):

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)

    def test_parse_minimal_glc_returns_expected_fields(self) -> None:
        # time_end is no longer a GLC field (issue #148): it is derived from the
        # image's pixel height at extraction, so the parser exposes only the
        # image filename and the two frequency-band values.
        doc = extract_to_csv.parse_glc(FIXTURES / "minimal.glc")
        self.assertFalse(hasattr(doc, "time_end"))
        self.assertEqual(doc.bandwidth, "400")
        self.assertEqual(doc.bandcentre, "200")
        self.assertEqual(doc.image_filename, "gram12.PNG")
        self.assertEqual(doc.warnings, [])

    def test_parse_malformed_glc_returns_empty_with_warning(self) -> None:
        doc = extract_to_csv.parse_glc(FIXTURES / "malformed.glc")
        self.assertEqual(doc.image_filename, "")
        self.assertEqual(doc.bandwidth, "")
        self.assertEqual(doc.bandcentre, "")
        self.assertEqual(len(doc.warnings), 1)
        self.assertTrue(doc.warnings[0].startswith("GLC malformed:"))

    def test_parse_glc_strips_windows_path(self) -> None:
        path = TMP / "windows_path.glc"
        path.write_text(
            "<GAPS_Lite_configuration>"
            "<data_source><filename>W:\\foo\\bar\\file.PNG</filename>"
            "<bitmap_crop_values><bottom_crop>10</bottom_crop></bitmap_crop_values>"
            "</data_source>"
            "<settings><lofar><bandwidth>100</bandwidth></lofar></settings>"
            "</GAPS_Lite_configuration>",
            encoding="utf-8",
        )
        doc = extract_to_csv.parse_glc(path)
        self.assertEqual(doc.image_filename, "file.PNG")

    def test_parse_glc_records_missing_element_warnings(self) -> None:
        path = TMP / "missing_elements.glc"
        path.write_text(
            "<GAPS_Lite_configuration>"
            "<data_source><bitmap_crop_values></bitmap_crop_values></data_source>"
            "<settings><lofar></lofar></settings>"
            "</GAPS_Lite_configuration>",
            encoding="utf-8",
        )
        doc = extract_to_csv.parse_glc(path)
        self.assertIn("GLC missing filename", doc.warnings)
        # bottom_crop is no longer read, so its absence is no longer warned
        # (issue #148 — it was spurious "invalid GLC" noise on valid images).
        self.assertNotIn("GLC missing bottom_crop", doc.warnings)
        self.assertIn("GLC missing bandwidth", doc.warnings)
        self.assertIn("GLC missing bandcentre", doc.warnings)

    def test_parse_glc_reads_bandcentre(self) -> None:
        """The frequency band is bandwidth + bandcentre (issue #87)."""
        path = TMP / "off_centre.glc"
        path.write_text(
            "<GAPS_Lite_configuration>"
            "<data_source><filename>g.png</filename>"
            "<bitmap_crop_values><bottom_crop>300</bottom_crop></bitmap_crop_values>"
            "</data_source>"
            "<settings><lofar>"
            "<bandwidth>400</bandwidth><bandcentre>600</bandcentre>"
            "</lofar></settings>"
            "</GAPS_Lite_configuration>",
            encoding="utf-8",
        )
        doc = extract_to_csv.parse_glc(path)
        self.assertEqual(doc.bandwidth, "400")
        self.assertEqual(doc.bandcentre, "600")
        self.assertEqual(doc.warnings, [])

    def test_parse_glc_missing_bandcentre_warns_keeps_bandwidth(self) -> None:
        path = TMP / "no_centre.glc"
        path.write_text(
            "<GAPS_Lite_configuration>"
            "<data_source><filename>g.png</filename>"
            "<bitmap_crop_values><bottom_crop>300</bottom_crop></bitmap_crop_values>"
            "</data_source>"
            "<settings><lofar><bandwidth>400</bandwidth></lofar></settings>"
            "</GAPS_Lite_configuration>",
            encoding="utf-8",
        )
        doc = extract_to_csv.parse_glc(path)
        self.assertEqual(doc.bandwidth, "400")
        self.assertEqual(doc.bandcentre, "")
        self.assertIn("GLC missing bandcentre", doc.warnings)
        self.assertNotIn("GLC missing bandwidth", doc.warnings)


if __name__ == "__main__":
    unittest.main()
