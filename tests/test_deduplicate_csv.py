"""Tests for deduplicate_csv.py (feature 006, User Story 3).

Covers the strict threshold, content-confirmed grouping, first-occurrence
master nomination, missing-asset tolerance, and the CSV round-trip /
idempotency contract. The shared fixture is ``tests/fixtures/dedup_source.csv``
plus the asset files under ``tests/fixtures/dedup/``.
"""

from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import deduplicate_csv  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures"
TMP = REPO_ROOT / "tests" / "_tmp"
SOURCE = FIXTURES / "dedup_source.csv"


def _read(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or ()), [dict(r) for r in reader]


class DeduplicateCsvTests(unittest.TestCase):

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = TMP / f"dedup_csv_{self._testMethodName}"
        if self.tmp.exists():
            import shutil
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _run(self, out_name="out.csv", threshold=None) -> Path:
        out = self.tmp / out_name
        argv = ["--csv", str(SOURCE), "--image-root", str(FIXTURES), "--out", str(out)]
        if threshold is not None:
            argv += ["--threshold-bytes", str(threshold)]
        self.assertEqual(deduplicate_csv.main(argv), 0)
        return out

    def _by_png(self, rows) -> dict:
        return {r["png_path"]: r["master_png_path"] for r in rows}

    # -- T031: first occurrence is master -----------------------------------
    def test_first_occurrence_is_master(self) -> None:
        _, rows = _read(self._run())
        m = self._by_png(rows)
        # Audio group: gram 20 (master.wav) is first -> empty; dup1/dup2 redirect.
        self.assertEqual(m["dedup/audio/master.wav"], "")
        self.assertEqual(m["dedup/audio/dup1.wav"], "dedup/audio/master.wav")
        self.assertEqual(m["dedup/audio/dup2.wav"], "dedup/audio/master.wav")
        # Image group: shared.png master; shared_b.png redirects.
        self.assertEqual(m["dedup/img/shared.png"], "")
        self.assertEqual(m["dedup/img/shared_b.png"], "dedup/img/shared.png")

    # -- T030: strict threshold ---------------------------------------------
    def test_strict_threshold(self) -> None:
        _, rows = _read(self._run())
        m = self._by_png(rows)
        # Small duplicated pair (<= 10 MiB) is never redirected.
        self.assertEqual(m["dedup/img/small_a.png"], "")
        self.assertEqual(m["dedup/img/small_b.png"], "")

    def test_threshold_override_excludes_all(self) -> None:
        # A threshold above every file_size makes nothing a candidate.
        _, rows = _read(self._run("hi.csv", threshold=99_000_000))
        self.assertTrue(all(r["master_png_path"] == "" for r in rows))

    # -- T032: unique large untouched + sha256 confirmation -----------------
    def test_unique_large_untouched(self) -> None:
        _, rows = _read(self._run())
        m = self._by_png(rows)
        # unique.png shares file_size with the image group but differs in
        # content -> sha256 separates it -> never redirected.
        self.assertEqual(m["dedup/img/unique.png"], "")

    def test_size_collision_confirmed_by_hash(self) -> None:
        # The audio .wav and the image .png share file_size (11_000_000) but
        # are byte-different; they must NOT be grouped together.
        _, rows = _read(self._run())
        m = self._by_png(rows)
        self.assertNotEqual(m["dedup/audio/dup1.wav"], "dedup/img/shared.png")
        self.assertEqual(m["dedup/audio/dup1.wav"], "dedup/audio/master.wav")

    # -- T033: missing asset left unredirected with WARNING -----------------
    def test_missing_asset_left_unredirected_with_warning(self) -> None:
        # Build a CSV whose only candidate pair points at a non-existent file.
        bad = self.tmp / "bad.csv"
        cols = ["publication", "chapter", "gram_id", "vessel_name", "topic_type",
                "sequence", "topic_filename", "display_text", "link_href",
                "glc_path", "time_end", "freq_end", "png_path", "file_size",
                "wav_treatment", "warnings"]
        with bad.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, quoting=csv.QUOTE_MINIMAL,
                               lineterminator="\r\n")
            w.writeheader()
            for gid, png in (("40", "dedup/missing_a.wav"), ("41", "dedup/missing_b.wav")):
                w.writerow({c: "" for c in cols} | {
                    "publication": "main", "chapter": "X", "gram_id": gid,
                    "topic_type": "glc", "sequence": "1", "png_path": png,
                    "file_size": "11000000",
                })
        out = self.tmp / "bad_out.csv"
        self.assertEqual(deduplicate_csv.main(
            ["--csv", str(bad), "--image-root", str(FIXTURES), "--out", str(out)]), 0)
        _, rows = _read(out)
        self.assertTrue(all(r["master_png_path"] == "" for r in rows))
        log = Path("dedup.log").read_text(encoding="utf-8")
        self.assertIn("missing/unreadable", log)

    # -- T034: round-trip fidelity + idempotency ----------------------------
    def test_csv_roundtrip_and_idempotent(self) -> None:
        out1 = self._run("once.csv")
        # master_png_path appended at the right edge.
        fieldnames, _ = _read(out1)
        self.assertEqual(fieldnames[-1], "master_png_path")
        # File-level contract: BOM + CRLF preserved.
        raw = out1.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "utf-8-sig BOM preserved")
        self.assertIn(b"\r\n", raw)
        # Author (non-identity) columns are untouched.
        _, src_rows = _read(SOURCE)
        _, out_rows = _read(out1)
        for s, o in zip(src_rows, out_rows):
            self.assertEqual(s["display_text"], o["display_text"])
            self.assertEqual(s["png_path"], o["png_path"])
        # Idempotent: a second run over the same inputs is byte-identical.
        out2 = self._run("twice.csv")
        self.assertEqual(out1.read_bytes(), out2.read_bytes())
        # And re-running over an already-deduplicated CSV is stable too.
        out3 = self.tmp / "thrice.csv"
        self.assertEqual(deduplicate_csv.main(
            ["--csv", str(out1), "--image-root", str(FIXTURES), "--out", str(out3)]), 0)
        self.assertEqual(out1.read_bytes(), out3.read_bytes())


if __name__ == "__main__":
    unittest.main()
