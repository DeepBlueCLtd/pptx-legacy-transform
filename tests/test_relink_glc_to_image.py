"""Tests for relink_glc_to_image.py.

Exercises the two filename-matching conventions (descriptive-suffix and
numbered-wav), the warn-and-skip behaviour on no/ambiguous matches, the
byte-level minimal-churn rewrite, and idempotency on re-run. Stdlib-only.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import relink_glc_to_image as relink  # noqa: E402

GLC_TEMPLATE = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    "<GAPS_Lite_configuration><data_source><filename>{name}</filename>"
    "<bitmap_crop_values><top_crop>0</top_crop><bottom_crop>271</bottom_crop>"
    "</bitmap_crop_values></data_source><playback><time_offset>0</time_offset>"
    "</playback><settings><lofar><bandwidth>200</bandwidth>"
    "<bandcentre>100</bandcentre></lofar></settings></GAPS_Lite_configuration>"
)


class RelinkTestBase(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def folder(self, name: str = "gram-01") -> Path:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_glc(self, folder: Path, glc_name: str, inner: str) -> Path:
        path = folder / glc_name
        path.write_text(GLC_TEMPLATE.format(name=inner), encoding="utf-8")
        return path

    def touch(self, folder: Path, name: str, data: bytes = b"x") -> Path:
        path = folder / name
        path.write_bytes(data)
        return path

    def inner_filename(self, glc_path: Path) -> str:
        return relink.parse_glc(glc_path).image_filename


class MatchingTests(RelinkTestBase):

    def test_pattern_a_descriptive_suffix(self) -> None:  # Pattern A
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "45 - 99 Hz.wav")
        self.touch(d, "45 - 99 Hz.wav")
        self.touch(d, "Image 1-45 - 99 Hz.jpg")

        self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(self.inner_filename(glc), "Image 1-45 - 99 Hz.jpg")
        self.assertFalse((d / "45 - 99 Hz.wav").exists())
        self.assertTrue((d / "45 - 99 Hz.wav.bak").exists())

    def test_pattern_b_numbered_wav(self) -> None:  # Pattern B
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "WAV 1.wav")
        self.touch(d, "WAV 1.wav")
        self.touch(d, "Image 1-0-110 Hz.jpg")

        self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(self.inner_filename(glc), "Image 1-0-110 Hz.jpg")
        self.assertTrue((d / "WAV 1.wav.bak").exists())

    def test_two_pairs_in_one_folder_no_cross_match(self) -> None:
        d = self.folder()
        glc_a = self.write_glc(d, "lofar-1.glc", "45 - 99 Hz.wav")
        glc_b = self.write_glc(d, "lofar-2.glc", "100 - 200 Hz.wav")
        self.touch(d, "45 - 99 Hz.wav")
        self.touch(d, "100 - 200 Hz.wav")
        self.touch(d, "Image 1-45 - 99 Hz.jpg")
        self.touch(d, "Image 2-100 - 200 Hz.jpg")

        self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(self.inner_filename(glc_a), "Image 1-45 - 99 Hz.jpg")
        self.assertEqual(self.inner_filename(glc_b), "Image 2-100 - 200 Hz.jpg")

    def test_no_candidate_leaves_glc_and_wav_untouched(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "45 - 99 Hz.wav")
        wav = self.touch(d, "45 - 99 Hz.wav")
        original = glc.read_text(encoding="utf-8")

        with self.assertLogs(relink.LOGGER, level="WARNING") as cm:
            self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(glc.read_text(encoding="utf-8"), original)
        self.assertTrue(wav.exists())
        self.assertTrue(any("no candidate image" in m for m in cm.output))

    def test_ambiguous_match_skips_with_warning(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "99 Hz.wav")
        self.touch(d, "99 Hz.wav")
        self.touch(d, "Image 1-45 - 99 Hz.jpg")
        self.touch(d, "Image 2-200 - 99 Hz.jpg")
        original = glc.read_text(encoding="utf-8")

        with self.assertLogs(relink.LOGGER, level="WARNING") as cm:
            self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(glc.read_text(encoding="utf-8"), original)
        self.assertTrue(any("ambiguous" in m for m in cm.output))

    def test_preexisting_non_image_named_file_is_not_candidate(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "Lofar 1 I.wav")
        self.touch(d, "Lofar 1 I.wav")
        # A pre-existing topic image, not an "Image <N>-" replacement.
        self.touch(d, "lofar-1-i.png")
        original = glc.read_text(encoding="utf-8")

        self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(glc.read_text(encoding="utf-8"), original)


class IdempotencyTests(RelinkTestBase):

    def test_glc_already_image_is_ignored(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "Image 1-45 - 99 Hz.jpg")
        self.touch(d, "Image 1-45 - 99 Hz.jpg")
        original = glc.read_text(encoding="utf-8")

        self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(glc.read_text(encoding="utf-8"), original)

    def test_second_run_is_noop(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "45 - 99 Hz.wav")
        self.touch(d, "45 - 99 Hz.wav")
        self.touch(d, "Image 1-45 - 99 Hz.jpg")

        self.assertEqual(relink.main(["--root", str(self.root)]), 0)
        after_first = glc.read_text(encoding="utf-8")
        self.assertEqual(relink.main(["--root", str(self.root)]), 0)
        self.assertEqual(glc.read_text(encoding="utf-8"), after_first)


class RewriteTests(RelinkTestBase):

    def test_rewrite_changes_only_filename_text(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "45 - 99 Hz.wav")
        before = glc.read_text(encoding="utf-8")

        relink.rewrite_glc_filename(glc, "Image 1-45 - 99 Hz.jpg")

        after = glc.read_text(encoding="utf-8")
        expected = before.replace("45 - 99 Hz.wav", "Image 1-45 - 99 Hz.jpg")
        self.assertEqual(after, expected)

    def test_dry_run_writes_nothing(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "45 - 99 Hz.wav")
        wav = self.touch(d, "45 - 99 Hz.wav")
        self.touch(d, "Image 1-45 - 99 Hz.jpg")  # a real match exists
        original = glc.read_text(encoding="utf-8")

        with self.assertLogs(relink.LOGGER, level="INFO") as cm:
            self.assertEqual(relink.main(["--root", str(self.root), "--dry-run"]), 0)

        # A match was found and reported, but nothing on disk changed.
        self.assertTrue(any("[dry-run] would relink" in m for m in cm.output))
        self.assertEqual(glc.read_text(encoding="utf-8"), original)
        self.assertTrue(wav.exists())
        self.assertFalse((d / "45 - 99 Hz.wav.bak").exists())

    def test_missing_wav_still_relinks_with_warning(self) -> None:
        d = self.folder()
        glc = self.write_glc(d, "lofar-1.glc", "45 - 99 Hz.wav")
        # No wav on disk, but the image is present.
        self.touch(d, "Image 1-45 - 99 Hz.jpg")

        with self.assertLogs(relink.LOGGER, level="WARNING") as cm:
            self.assertEqual(relink.main(["--root", str(self.root)]), 0)

        self.assertEqual(self.inner_filename(glc), "Image 1-45 - 99 Hz.jpg")
        self.assertTrue(any("nothing to move aside" in m for m in cm.output))


if __name__ == "__main__":
    unittest.main()
