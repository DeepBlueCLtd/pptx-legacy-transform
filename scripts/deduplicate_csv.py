"""Large-asset deduplication post-processor (feature 006, User Story 3).

Reads a signed-off intermediate CSV, detects large (>10 MiB by default)
*content-duplicate* assets, and writes a copy of the CSV with the optional
``master_png_path`` column populated: within each group of byte-identical
large assets the first occurrence (in deterministic row-identity order)
becomes the master and the remaining occurrences are pointed at it. The
generator (``generate_dita.py``) then links every redirected lofar to the
single master copy instead of copying its own asset.

Byte-identity alone is not sufficient for ``.wav`` rows (issue #78): an
audio lofar's link target is its ``.glc``, and two ``.glc`` files can
present different time/frequency windows onto the same recording. A
``.wav`` row therefore only joins a duplicate group when its extracted
``(time_end, bandwidth, bandcentre)`` view also matches; rows sharing the
bytes but not the view each keep their own ``.glc``/``.wav`` pair.

This step is **opt-in** and **inert-safe**: assets at or below the
threshold, or used only once, are never redirected, and a CSV the operator
never runs this over keeps the column absent (the export stays
byte-for-byte as today, FR-010). Re-running over the same inputs yields a
byte-identical CSV (FR-013, SC-006).

Logging convention (R10): dual stdout + ``dedup.log`` per-stage file
handlers, mirroring ``generate_dita.py`` / ``extract_to_csv.py`` so the
air-gapped maintainer reads one shape of code in every script. Detection
is scoped to genuine candidates — only rows whose ``file_size`` exceeds the
threshold are considered, and a large file with a unique ``file_size`` is
never hashed (it cannot have a byte-identical twin).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

# The optional right-edge columns this script populates. Kept in lockstep
# with ``generate_dita.OPTIONAL_CSV_COLUMNS``.
MASTER_PNG_PATH = "master_png_path"
# The renumbered gram number (feature 008). Empty means "unchanged — use
# ``gram_id``"; ``gram_id`` itself is never mutated.
TARGET_GRAM_ID = "target_gram_id"

# Default candidacy cut-off: strictly greater than 10 MiB (FR-003). The
# mebibyte reading of the user's "10Mb" cut-off; overridable via CLI.
DEFAULT_THRESHOLD_BYTES = 10 * 1024 * 1024

LOGGER = logging.getLogger(__name__)


def setup_logging(log_path: Path) -> None:
    """Configure dual stdout + per-stage-file logging (mirrors generate_dita)."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.INFO)
    stream.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.setLevel(logging.DEBUG)
    root.addHandler(stream)
    root.addHandler(file_handler)


# -----------------------------------------------------------------------------
# CSV I/O — preserve the file-level contract (utf-8-sig, CRLF, QUOTE_MINIMAL)
# -----------------------------------------------------------------------------

def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    """Return ``(fieldnames, rows)`` from the intermediate CSV.

    The header is preserved verbatim so the output can round-trip every
    existing column; only ``master_png_path`` is added if absent.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or ())
        rows = [dict(r) for r in reader]
    return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write ``rows`` preserving the Excel-friendly CSV contract.

    UTF-8 with BOM (``utf-8-sig``), ``,`` delimiter, ``QUOTE_MINIMAL``,
    ``\\r\\n`` line terminator — identical to what ``extract_to_csv.py``
    emits, so the technical author's Excel round-trip behaves.
    """
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=fieldnames,
            quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in fieldnames})


# -----------------------------------------------------------------------------
# Detection
# -----------------------------------------------------------------------------

def _identity_key(row: dict) -> tuple:
    """Row-identity tuple used for deterministic master nomination.

    ``(publication, chapter, gram_id, topic_type, sequence)`` — the first
    occurrence in this order within a duplicate group is the master.
    """
    return (
        row.get("publication", ""), row.get("chapter", ""),
        row.get("gram_id", ""), row.get("topic_type", ""),
        row.get("sequence", ""),
    )


def _parse_size(row: dict) -> int | None:
    """Return ``int(file_size)`` or ``None`` if the cell is absent/unparseable."""
    raw = (row.get("file_size", "") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _view_key(row: dict) -> tuple:
    """Sub-grouping key applied within a byte-identical duplicate group.

    An audio lofar's link target is its ``.glc``, not the ``.wav`` it
    names (FR-009), and two ``.glc`` files can window the same recording
    differently. Byte-identical ``.wav`` rows are therefore
    interchangeable only when the extracted view matches: they merge only
    on equal ``(time_end, bandwidth, bandcentre)`` (issues #78, #87 — the
    frequency view is the band pair, not a single upper limit). A ``.wav``
    row missing ``time_end`` or ``bandwidth`` gets a unique key and is never
    merged — dropping a distinct student view is worse than missing a
    reclamation. A blank ``bandcentre`` is a legitimate value (legacy band
    centred at ``bandwidth/2``) and participates in the key as-is. Non-wav
    assets carry their view in the row itself (the gram-config table), so
    byte-identity alone suffices and they share one key.
    """
    png = (row.get("png_path", "") or "").strip()
    if Path(png).suffix.lower() != ".wav":
        return ("any",)
    time_end = (row.get("time_end", "") or "").strip()
    bandwidth = (row.get("bandwidth", "") or "").strip()
    bandcentre = (row.get("bandcentre", "") or "").strip()
    if not time_end or not bandwidth:
        return ("wav-view-unknown",) + _identity_key(row)
    return ("wav-view", time_end, bandwidth, bandcentre)


def _hash_file(image_root: Path, png_path: str) -> str | None:
    """Return the sha256 hex digest of ``image_root / png_path`` or ``None``.

    ``None`` means the file is missing or unreadable — the row is then left
    non-redirected with a WARNING (it is not a confirmed duplicate, FR-014).
    """
    source = image_root / png_path
    try:
        h = hashlib.sha256()
        with source.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError as exc:
        LOGGER.warning(
            "Asset missing/unreadable, left non-redirected: %s (%s)", source, exc,
        )
        return None


def deduplicate(
    rows: list[dict], image_root: Path, threshold_bytes: int,
) -> int:
    """Populate each row's ``master_png_path`` in place; return redirect count.

    Candidacy: ``file_size`` strictly greater than ``threshold_bytes``
    (FR-003). Candidates are grouped by ``file_size`` first; only within a
    size-collision group of >=2 is content confirmed by ``sha256`` (a
    unique-size large file is never hashed). Confirmed byte-identical
    rows are then split by ``_view_key`` so ``.wav`` rows merge only when
    their ``(time_end, bandwidth, bandcentre)`` view also matches (issues
    #78, #87). Within
    each resulting group of >=2, the first row by ``_identity_key`` is
    the master (empty ``master_png_path``); the rest carry the master's
    ``png_path``.
    """
    # Every row starts non-redirected; this also repopulates (clears stale
    # values from) a CSV that already carries the column, keeping the
    # operation idempotent.
    for row in rows:
        row[MASTER_PNG_PATH] = ""

    # 1) Candidate filter + size pre-grouping.
    by_size: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        size = _parse_size(row)
        png = (row.get("png_path", "") or "").strip()
        if size is not None and size > threshold_bytes and png:
            by_size[size].append(row)

    redirected = 0
    total_reclaimed = 0
    # 2) Confirm content identity only inside size-collision groups of >=2.
    for size in sorted(by_size):
        members = by_size[size]
        if len(members) < 2:
            continue  # unique size — cannot have a byte-identical twin
        by_hash: dict[str, list[dict]] = defaultdict(list)
        for row in members:
            digest = _hash_file(image_root, row["png_path"])
            if digest is not None:
                by_hash[digest].append(row)
        # 3) Nominate master + redirect within each confirmed group. A
        #    byte-identical set is split by view first: .wav rows merge
        #    only when (time_end, bandwidth, bandcentre) also match (#78, #87).
        for digest in sorted(by_hash):
            members = by_hash[digest]
            if len(members) < 2:
                continue
            by_view: dict[tuple, list[dict]] = defaultdict(list)
            for row in members:
                key = _view_key(row)
                if key[0] == "wav-view-unknown":
                    LOGGER.warning(
                        "Byte-identical .wav left non-redirected: %s "
                        "(gram %s seq %s) is missing time_end/bandwidth, so "
                        "its .glc view cannot be confirmed to match",
                        row.get("png_path", ""), row.get("gram_id", ""),
                        row.get("sequence", ""),
                    )
                by_view[key].append(row)
            for view in sorted(by_view):
                group = by_view[view]
                if len(group) < 2:
                    continue
                group.sort(key=_identity_key)
                master = group[0]
                master_png = master.get("png_path", "")
                count = 0
                for row in group[1:]:
                    row[MASTER_PNG_PATH] = master_png
                    count += 1
                redirected += count
                reclaimed = count * size
                total_reclaimed += reclaimed
                LOGGER.info(
                    "Duplicate group: master=%s%s redirected=%d bytes_reclaimed=%d",
                    master_png,
                    " view=%s/%s/%s" % (view[1], view[2], view[3]) if view[0] == "wav-view" else "",
                    count, reclaimed,
                )

    LOGGER.info(
        "Deduplication summary: groups_redirected_rows=%d total_bytes_reclaimed=%d",
        redirected, total_reclaimed,
    )
    return redirected


# -----------------------------------------------------------------------------
# Gram renumbering (feature 008) — resolve within-week gram-number collisions
# -----------------------------------------------------------------------------

_DIGITS_RE = re.compile(r"\d+")


def _effective_chapter(row: dict) -> str:
    """``target_chapter`` when set, else the immutable source ``chapter``."""
    return (row.get("target_chapter", "") or "").strip() or row.get("chapter", "")


def _effective_doc(row: dict) -> str:
    return (row.get("target_doc", "") or "").strip()


def _gram_number(gram_id: str) -> int | None:
    """Return the leading integer of ``gram_id`` (e.g. ``"Gram 05"`` → 5)."""
    match = _DIGITS_RE.search(gram_id or "")
    return int(match.group()) if match else None


def _week_sort_key(effective_chapter: str) -> tuple:
    """Order numeric week chapters (1,2,3,4) ahead of any non-numeric effective
    chapter, each group then by value / string. Used to walk ``main`` grams in
    week order for the continuous scheme."""
    ec = (effective_chapter or "").strip()
    return (0, int(ec)) if ec.isdigit() else (1, ec)


def _renumber_buckets(rows: list[dict], indices) -> int:
    """Per-week (feature 008) renumber over ``indices``.

    Within each ``(publication, effective_chapter, effective_doc)`` bucket, walk
    the distinct grams in ``(source chapter, first-row order)`` order; the first
    claimant of a number keeps it and any later gram whose number is already
    taken is reassigned to one greater than the bucket's current maximum. Native
    numbers are preserved; only genuine collisions move. ``gram_id`` is never
    mutated. Returns the count of renumbered grams.
    """
    buckets: dict[tuple, list[int]] = defaultdict(list)
    for idx in indices:
        row = rows[idx]
        bucket = (row.get("publication", ""), _effective_chapter(row), _effective_doc(row))
        buckets[bucket].append(idx)

    renumbered = 0
    for bucket in sorted(buckets):
        # Distinct grams within the bucket: unique (chapter, gram_id, vessel),
        # remembering the first row index so we can order and assign to all rows.
        gram_rows: dict[tuple, list[int]] = {}
        gram_first: dict[tuple, int] = {}
        for idx in buckets[bucket]:
            row = rows[idx]
            ident = (
                row.get("chapter", ""), row.get("gram_id", ""),
                row.get("vessel_name", ""),
            )
            if ident not in gram_rows:
                gram_rows[ident] = []
                gram_first[ident] = idx
            gram_rows[ident].append(idx)

        ordered = sorted(gram_rows, key=lambda ident: (ident[0], gram_first[ident]))
        used: set[int] = set()
        for ident in ordered:
            number = _gram_number(ident[1])
            if number is None:
                continue  # no numeric gram_id — nothing to renumber against
            if number in used:
                new_number = max(used) + 1
                for idx in gram_rows[ident]:
                    rows[idx][TARGET_GRAM_ID] = str(new_number)
                LOGGER.info(
                    "gram renumbered: chapter=%s gram_id=%s -> %d",
                    _effective_chapter(rows[gram_first[ident]]), ident[1], new_number,
                )
                used.add(new_number)
                renumbered += 1
            else:
                used.add(number)
    return renumbered


def _renumber_main_continuous(rows: list[dict], indices) -> int:
    """Continuous ``main`` numbering (feature 009): one ``1..N`` sequence across
    the four weeks, ordered by ``(week, source chapter, first-row order)`` so
    week N starts at one past week N-1's maximum. A gram whose ``gram_id``
    already equals its assigned number keeps an empty ``target_gram_id``
    (effective number == gram_id); ``gram_id`` is never mutated. Returns the
    count of renumbered grams.
    """
    gram_rows: dict[tuple, list[int]] = {}
    gram_first: dict[tuple, int] = {}
    gram_week: dict[tuple, tuple] = {}
    gram_chapter: dict[tuple, str] = {}
    for idx in indices:
        row = rows[idx]
        ident = (
            row.get("chapter", ""), row.get("gram_id", ""),
            row.get("vessel_name", ""),
        )
        if ident not in gram_rows:
            gram_rows[ident] = []
            gram_first[ident] = idx
            gram_week[ident] = _week_sort_key(_effective_chapter(row))
            gram_chapter[ident] = row.get("chapter", "")
        gram_rows[ident].append(idx)

    ordered = sorted(
        gram_rows,
        key=lambda ident: (gram_week[ident], gram_chapter[ident], gram_first[ident]),
    )
    renumbered = 0
    for seq, ident in enumerate(ordered, start=1):
        if _gram_number(ident[1]) == seq:
            continue  # already this number — leave target_gram_id empty
        for idx in gram_rows[ident]:
            rows[idx][TARGET_GRAM_ID] = str(seq)
        LOGGER.info(
            "main gram renumbered (continuous): chapter=%s gram_id=%s -> %d",
            _effective_chapter(rows[gram_first[ident]]), ident[1], seq,
        )
        renumbered += 1
    return renumbered


def renumber_grams(rows: list[dict], main_numbering: str = "per-week") -> int:
    """Populate ``target_gram_id`` to give grams collision-free numbers.

    ``main_numbering`` (feature 009) selects how the ``main`` publication is
    numbered; non-``main`` publications always use the per-week rule:

    - ``"per-week"`` (default): every publication, ``main`` included, is numbered
      **per week** — within each ``(publication, effective_chapter,
      effective_doc)`` bucket native numbers are preserved and only genuine
      collisions are bumped (the feature-008 behaviour; unique per week, not
      globally).
    - ``"continuous"``: ``main`` is numbered as one ``1..N`` sequence across the
      four weeks (week N starts past week N-1's maximum); non-``main`` keeps the
      per-week rule.

    Idempotent: ``target_gram_id`` is cleared and recomputed from ``gram_id``
    each run, so re-running over the same inputs and scheme yields a
    byte-identical CSV. ``gram_id`` is never mutated. Returns the count of
    renumbered grams.
    """
    # Reset so a CSV that already carries the column recomputes cleanly.
    for row in rows:
        row[TARGET_GRAM_ID] = ""

    if main_numbering == "continuous":
        main_idx = [i for i, r in enumerate(rows) if r.get("publication", "") == "main"]
        nonmain_idx = [i for i, r in enumerate(rows) if r.get("publication", "") != "main"]
        renumbered = (
            _renumber_main_continuous(rows, main_idx)
            + _renumber_buckets(rows, nonmain_idx)
        )
    else:
        # per-week (default): feature-008 behaviour for every publication (main
        # is per-week because effective_doc is "" for main).
        renumbered = _renumber_buckets(rows, range(len(rows)))

    LOGGER.info(
        "Renumber summary: grams_renumbered=%d (main_numbering=%s)",
        renumbered, main_numbering,
    )
    return renumbered


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Post-process the signed-off CSV: redirect duplicate large "
                    "assets to a single master copy (feature 006).",
    )
    parser.add_argument("--csv", required=True, type=Path, dest="csv_path",
                        help="input signed-off CSV")
    parser.add_argument("--image-root", required=True, type=Path, dest="image_root",
                        help="root the png_path cells resolve against (for hashing)")
    parser.add_argument("--out", required=True, type=Path,
                        help="output CSV path (may equal --csv to rewrite in place)")
    parser.add_argument("--threshold-bytes", type=int,
                        default=DEFAULT_THRESHOLD_BYTES, dest="threshold_bytes",
                        help="candidacy cut-off; only rows with file_size "
                             "strictly greater are eligible (default 10 MiB)")
    parser.add_argument("--main-numbering", choices=("per-week", "continuous"),
                        default="per-week", dest="main_numbering",
                        help="how the main publication's grams are numbered "
                             "(feature 009): 'per-week' (default) keeps numbering "
                             "unique within each week, preserving native numbers "
                             "and bumping only collisions; 'continuous' numbers "
                             "main as one 1..N sequence across the four weeks. "
                             "Non-main publications are unaffected.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    setup_logging(Path("dedup.log"))

    if not args.csv_path.is_file():
        LOGGER.error("CSV does not exist: %s", args.csv_path)
        return 1

    try:
        fieldnames, rows = read_csv(args.csv_path)
    except Exception as exc:
        LOGGER.error("Failed to read CSV: %s", exc)
        return 1

    for column in (MASTER_PNG_PATH, TARGET_GRAM_ID):
        if column not in fieldnames:
            fieldnames = fieldnames + [column]

    renumber_grams(rows, main_numbering=args.main_numbering)
    deduplicate(rows, args.image_root, args.threshold_bytes)

    try:
        write_csv(args.out, fieldnames, rows)
    except Exception as exc:
        LOGGER.error("Failed to write CSV: %s", exc)
        return 1
    LOGGER.info("Wrote deduplicated CSV %s", args.out)
    return 0


if __name__ == "__main__":
    rc = main()
    # Match generate_dita.py: preserve CLI exit codes when run as a script
    # but stay silent under an interactive REPL (sys.ps1 only set there).
    if rc and not hasattr(sys, "ps1"):
        sys.exit(rc)
