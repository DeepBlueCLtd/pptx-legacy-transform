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
        # The post-processor's optional columns are appended at the right edge,
        # in lockstep with generate_dita.OPTIONAL_CSV_COLUMNS: master_png_path
        # (feature 006) then target_gram_id (feature 008).
        fieldnames, _ = _read(out1)
        self.assertEqual(fieldnames[-2:], ["master_png_path", "target_gram_id"])
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


class RenumberGramsTests(unittest.TestCase):
    """Within-week gram-number renumbering (feature 008)."""

    @staticmethod
    def _gram(chapter, gram_id, vessel, target_chapter=""):
        """Two rows (analysis + one glc) sharing one gram's identity."""
        base = {
            "publication": "main", "chapter": chapter, "gram_id": gram_id,
            "vessel_name": vessel, "target_chapter": target_chapter,
            "target_doc": "",
        }
        return [
            {**base, "topic_type": "glc", "sequence": "1"},
            {**base, "topic_type": "analysis", "sequence": "1"},
        ]

    def _target(self, rows):
        """The target_gram_id assigned to each distinct gram, first row wins."""
        out = {}
        for r in rows:
            key = (r["chapter"], r["gram_id"], r["vessel_name"])
            out.setdefault(key, r["target_gram_id"])
        return out

    def test_collision_bumps_to_max_plus_one(self) -> None:
        # A week (target_chapter=2) with native grams 1,2,5 and a Pub10 gram
        # also claiming 5. Source chapter "A native" sorts before "B pub10",
        # so the native grams keep their numbers and Pub10 is bumped to 6.
        rows = (
            self._gram("A native", "1", "V1", "2")
            + self._gram("A native", "2", "V2", "2")
            + self._gram("A native", "5", "V5", "2")
            + self._gram("B pub10", "5", "VP", "2")
        )
        count = deduplicate_csv.renumber_grams(rows)
        self.assertEqual(count, 1)
        targets = self._target(rows)
        self.assertEqual(targets[("A native", "5", "V5")], "")  # native keeps 5
        self.assertEqual(targets[("B pub10", "5", "VP")], "6")  # bumped past max(5)
        # Non-colliding native grams are untouched.
        self.assertEqual(targets[("A native", "1", "V1")], "")
        self.assertEqual(targets[("A native", "2", "V2")], "")

    def test_order_is_alphabetical_by_source_chapter(self) -> None:
        # Same number 3 in two decks; the alphabetically-earlier chapter keeps
        # it regardless of CSV row order (the Pub10 deck is listed first here).
        rows = (
            self._gram("Z pub10", "3", "VP", "1")
            + self._gram("A week", "3", "VW", "1")
        )
        deduplicate_csv.renumber_grams(rows)
        targets = self._target(rows)
        self.assertEqual(targets[("A week", "3", "VW")], "")   # earlier chapter keeps 3
        self.assertEqual(targets[("Z pub10", "3", "VP")], "4")  # later chapter bumped

    def test_successive_collisions_step_the_maximum(self) -> None:
        rows = (
            self._gram("A", "1", "Va", "1")
            + self._gram("B", "1", "Vb", "1")
            + self._gram("C", "1", "Vc", "1")
        )
        deduplicate_csv.renumber_grams(rows)
        targets = self._target(rows)
        self.assertEqual(targets[("A", "1", "Va")], "")    # keeps 1
        self.assertEqual(targets[("B", "1", "Vb")], "2")   # max(1)+1
        self.assertEqual(targets[("C", "1", "Vc")], "3")   # max(2)+1

    def test_same_number_different_weeks_does_not_collide(self) -> None:
        rows = (
            self._gram("A week1", "5", "V1", "1")
            + self._gram("A week2", "5", "V2", "2")
        )
        count = deduplicate_csv.renumber_grams(rows)
        self.assertEqual(count, 0, "numbering is unique per week, not globally")
        self.assertTrue(all(r["target_gram_id"] == "" for r in rows))

    def test_inert_when_no_collision(self) -> None:
        rows = (
            self._gram("A", "1", "Va", "1")
            + self._gram("A", "2", "Vb", "1")
        )
        count = deduplicate_csv.renumber_grams(rows)
        self.assertEqual(count, 0)
        self.assertTrue(all(r["target_gram_id"] == "" for r in rows))

    def test_idempotent_recompute(self) -> None:
        rows = (
            self._gram("A native", "5", "V5", "2")
            + self._gram("B pub10", "5", "VP", "2")
        )
        deduplicate_csv.renumber_grams(rows)
        first = [r["target_gram_id"] for r in rows]
        # Re-running over the already-renumbered rows recomputes from gram_id.
        deduplicate_csv.renumber_grams(rows)
        self.assertEqual([r["target_gram_id"] for r in rows], first)


class ContinuousNumberingTests(unittest.TestCase):
    """Feature 009: ``--main-numbering continuous`` numbers ``main`` as one
    ``1..N`` sequence across the four weeks. The default (``per-week``) is the
    feature-008 behaviour exercised by ``RenumberGramsTests``."""

    @staticmethod
    def _gram(chapter, gram_id, vessel, target_chapter="", publication="main"):
        base = {
            "publication": publication, "chapter": chapter, "gram_id": gram_id,
            "vessel_name": vessel, "target_chapter": target_chapter,
            "target_doc": "",
        }
        return [
            {**base, "topic_type": "glc", "sequence": "1"},
            {**base, "topic_type": "analysis", "sequence": "1"},
        ]

    def _target(self, rows):
        out = {}
        for r in rows:
            out.setdefault(
                (r["chapter"], r["gram_id"], r["vessel_name"]), r["target_gram_id"],
            )
        return out

    def test_continuous_sequences_across_weeks(self) -> None:
        # Week 1 grams 1,2 ; Week 2 grams 1,2 → continuous 1,2,3,4 (week 2 → 3,4).
        rows = (
            self._gram("W1", "1", "Va", "1")
            + self._gram("W1", "2", "Vb", "1")
            + self._gram("W2", "1", "Vc", "2")
            + self._gram("W2", "2", "Vd", "2")
        )
        deduplicate_csv.renumber_grams(rows, main_numbering="continuous")
        t = self._target(rows)
        self.assertEqual(t[("W1", "1", "Va")], "")   # seq 1 == gram_id 1
        self.assertEqual(t[("W1", "2", "Vb")], "")   # seq 2 == gram_id 2
        self.assertEqual(t[("W2", "1", "Vc")], "3")  # week 2 starts past week 1
        self.assertEqual(t[("W2", "2", "Vd")], "4")

    def test_continuous_week_start_shifts_with_earlier_week_size(self) -> None:
        # 3 grams in week 1 → week 2 starts at 4 (the "week 2 starts at 35" case).
        rows = (
            self._gram("W1", "1", "A", "1") + self._gram("W1", "2", "B", "1")
            + self._gram("W1", "3", "C", "1")
            + self._gram("W2", "1", "D", "2") + self._gram("W2", "2", "E", "2")
        )
        deduplicate_csv.renumber_grams(rows, main_numbering="continuous")
        t = self._target(rows)
        self.assertEqual(t[("W2", "1", "D")], "4")
        self.assertEqual(t[("W2", "2", "E")], "5")

    def test_default_scheme_is_per_week(self) -> None:
        rows_default = self._gram("W1", "5", "A", "1") + self._gram("W2", "5", "B", "2")
        rows_explicit = self._gram("W1", "5", "A", "1") + self._gram("W2", "5", "B", "2")
        deduplicate_csv.renumber_grams(rows_default)  # no scheme → default
        deduplicate_csv.renumber_grams(rows_explicit, main_numbering="per-week")
        self.assertEqual(
            [r["target_gram_id"] for r in rows_default],
            [r["target_gram_id"] for r in rows_explicit],
        )
        # per-week keeps the same number in different weeks distinct (feature 008).
        self.assertTrue(all(r["target_gram_id"] == "" for r in rows_default))

    def test_non_main_unaffected_by_continuous(self) -> None:
        # Non-main publications keep per-week bump-on-collision under either scheme.
        rows = (
            self._gram("PT", "5", "Vp", "", publication="progress-test-1")
            + self._gram("PT", "5", "Vq", "", publication="progress-test-1")
        )
        deduplicate_csv.renumber_grams(rows, main_numbering="continuous")
        self.assertEqual(sorted(self._target(rows).values()), ["", "6"])

    def test_continuous_idempotent(self) -> None:
        rows = self._gram("W1", "1", "A", "1") + self._gram("W2", "9", "B", "2")
        deduplicate_csv.renumber_grams(rows, main_numbering="continuous")
        first = [r["target_gram_id"] for r in rows]
        deduplicate_csv.renumber_grams(rows, main_numbering="continuous")
        self.assertEqual([r["target_gram_id"] for r in rows], first)


if __name__ == "__main__":
    unittest.main()
