"""Large-asset deduplication post-processor (feature 006, User Story 3).

Reads a signed-off intermediate CSV, detects large (>10 MiB by default)
*content-duplicate* assets, and writes a copy of the CSV with the optional
``master_png_path`` column populated: within each group of byte-identical
large assets the first occurrence (in deterministic row-identity order)
becomes the master and the remaining occurrences are pointed at it. The
generator (``generate_dita.py``) then links every redirected lofar to the
single master copy instead of copying its own asset.

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
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

# The optional right-edge column this script populates. Kept in lockstep
# with ``generate_dita.OPTIONAL_CSV_COLUMNS``.
MASTER_PNG_PATH = "master_png_path"

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
    unique-size large file is never hashed). Within each confirmed
    byte-identical group of >=2, the first row by ``_identity_key`` is the
    master (empty ``master_png_path``); the rest carry the master's
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
        # 3) Nominate master + redirect within each confirmed group.
        for digest in sorted(by_hash):
            group = by_hash[digest]
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
                "Duplicate group: master=%s redirected=%d bytes_reclaimed=%d",
                master_png, count, reclaimed,
            )

    LOGGER.info(
        "Deduplication summary: groups_redirected_rows=%d total_bytes_reclaimed=%d",
        redirected, total_reclaimed,
    )
    return redirected


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

    if MASTER_PNG_PATH not in fieldnames:
        fieldnames = fieldnames + [MASTER_PNG_PATH]

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
