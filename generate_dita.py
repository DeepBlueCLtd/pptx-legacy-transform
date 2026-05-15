"""DITA generator (User Story 1, MVP).

Consumes the signed-off intermediate CSV and writes the DITA topic tree,
ditamaps, manifest, and skipped report under ``--out``. This is the
deliverable the migration pipeline exists to produce; everything before
this script feeds it.

Logging convention (R10): dual stdout + ``generate.log`` per-stage file
handlers, three levels (INFO/WARNING/ERROR), no silent exception
swallowing (FR-014). The single helper ``setup_logging`` mirrors the
identical helper in ``extract_to_csv.py`` and ``introspect_pptx.py`` so
the air-gapped maintainer reads one shape of code in every script.

Output is deterministic (sorted iteration, no embedded timestamps,
LF line endings, UTF-8 without BOM) so a second run over the same CSV
produces byte-identical files (R9, FR-013, SC-004).
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CSV_COLUMNS: tuple[str, ...] = (
    "publication", "chapter", "gram_id", "vessel_name", "topic_type",
    "sequence", "topic_filename", "display_text", "link_href", "glc_path",
    "time_end", "freq_end", "png_path", "wav_treatment", "warnings",
)

LOGGER = logging.getLogger(__name__)


def setup_logging(log_path: Path) -> None:
    """Configure dual stdout + per-stage-file logging."""
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
# CSV reader
# -----------------------------------------------------------------------------

def read_csv(path: Path) -> list[dict]:
    """Read the intermediate CSV with strict header validation (FR-014)."""
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        actual = tuple(reader.fieldnames or ())
        if actual != CSV_COLUMNS:
            raise ValueError(
                f"CSV header mismatch.\nExpected: {CSV_COLUMNS}\nActual:   {actual}"
            )
        rows = [dict(row) for row in reader]
    return rows


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lower-case, ASCII, hyphen-separated slug with collapsed runs (R3)."""
    ascii_only = text.encode("ascii", "ignore").decode("ascii").lower()
    return _SLUG_NON_ALNUM.sub("-", ascii_only).strip("-")


def slugify_asset_name(filename: str) -> str:
    """Slugify a filename while preserving its extension (lower-cased).

    Example: ``"Lofar 1 ABC.PNG"`` → ``"lofar-1-abc.png"``. The original
    extension is kept so DITA-OT and downstream consumers can still
    classify the asset by suffix.
    """
    p = Path(filename)
    stem = slugify(p.stem)
    suffix = p.suffix.lower()
    return f"{stem}{suffix}" if stem else f"asset{suffix}"


def resolve_image_href(png_path: str, image_root: Path, topic_dir: Path) -> str:
    """Return ``png_path`` resolved against ``image_root``, relative to ``topic_dir``."""
    if not png_path:
        return ""
    target = (image_root / png_path).resolve(strict=False)
    try:
        rel = target.relative_to(topic_dir.resolve(strict=False))
        return rel.as_posix()
    except ValueError:
        # Compute a relative POSIX path that may use ``..`` segments.
        import os
        rel_str = os.path.relpath(target, topic_dir.resolve(strict=False))
        return Path(rel_str).as_posix()


def copy_asset(
    src_relpath: str, image_root: Path, topic_dir: Path,
) -> tuple[str, Path | None]:
    """Copy the referenced asset next to its topic and return ``(href, written)``.

    The asset is renamed to a slugified version of its source filename
    (e.g. ``"Lofar 1 ABC.png"`` → ``"lofar-1-abc.png"``). Each gram has
    its own folder so two grams sharing an original filename never
    collide; the slug keeps hrefs URL-safe.

    If ``src_relpath`` is empty, returns ``("", None)``.

    If the source file is missing, a warning is logged and the intended
    local filename is still returned. The href in the topic XML therefore
    stays stable across runs, and dropping the asset in at the expected
    path and re-running the generator will resolve the dangling reference
    without any topic-file churn.
    """
    if not src_relpath:
        return "", None
    source = image_root / src_relpath
    target_name = slugify_asset_name(Path(src_relpath).name)
    target = topic_dir / target_name
    if source.is_file():
        topic_dir.mkdir(parents=True, exist_ok=True)
        # ``copy2`` preserves the source mtime so two consecutive generator
        # runs against an unchanged source tree produce byte- and stat-
        # identical assets, preserving the idempotency contract (R9).
        shutil.copy2(source, target)
        return target_name, target
    LOGGER.warning("Asset missing, href will dangle: %s", source)
    return target_name, None


def _gram_num(gram_id: str) -> str:
    digits = re.findall(r"\d+", gram_id)
    return digits[0] if digits else "00"


def _gram_folder_name(gram_id: str) -> str:
    """Return the per-gram folder name, e.g. ``"gram-01"``."""
    return f"gram-{_gram_num(gram_id)}"


def _publication_root(out_dir: Path, row: dict) -> Path:
    """Return the per-publication root, ``{out}/{pub}`` or ``{out}/main/{chapter}``."""
    pub = row["publication"]
    if pub.startswith("progress-test-"):
        return out_dir / pub
    chapter_slug = slugify(row.get("chapter", ""))
    return out_dir / "main" / chapter_slug


def _topic_dir_for_row(out_dir: Path, row: dict) -> Path:
    """Return the directory the topic + its asset live in.

    Each gram gets its own sub-directory so the original asset filenames
    can be preserved (slugified) without colliding across grams in the
    same chapter.
    """
    return _publication_root(out_dir, row) / _gram_folder_name(row["gram_id"])


# -----------------------------------------------------------------------------
# XML emission
# -----------------------------------------------------------------------------

def _serialise(root: ET.Element, leading: str = "") -> str:
    """Serialise ``root`` to a UTF-8 XML string with LF endings, no preamble."""
    body = ET.tostring(root, encoding="unicode")
    # ElementTree uses self-closing for empty elements; that matches the
    # contract examples (e.g. <image .../>, <link .../>).
    return f"{leading}{body}\n"


def emit_glc_topic(row: dict, out_dir: Path, image_root: Path) -> list[Path]:
    """Write ``gram_NN_lofarM.dita`` for a glc-typed row plus its asset."""
    gram_num = _gram_num(row["gram_id"])
    seq = row["sequence"]
    topic_id = f"gram_{gram_num}_lofar{seq}"
    topic_dir = _topic_dir_for_row(out_dir, row)
    topic_dir.mkdir(parents=True, exist_ok=True)
    topic_path = topic_dir / row["topic_filename"]

    image_href, copied = copy_asset(
        row.get("png_path", ""), image_root, topic_dir,
    )

    topic = ET.Element("topic", {"id": topic_id})
    title = ET.SubElement(topic, "title")
    title.text = f"Gram {gram_num}"
    if row.get("vessel_name"):
        ph = ET.SubElement(title, "ph", {"audience": "-trainee"})
        ph.text = f" - {row['vessel_name']}"

    body = ET.SubElement(topic, "body")
    section = ET.SubElement(body, "section")
    table = ET.SubElement(section, "table", {"outputclass": "gram-config"})
    tgroup = ET.SubElement(table, "tgroup", {"cols": "2"})
    tbody = ET.SubElement(tgroup, "tbody")

    image_row = ET.SubElement(tbody, "row")
    image_entry = ET.SubElement(image_row, "entry", {"namest": "c1", "nameend": "c2"})
    ET.SubElement(image_entry, "image", {
        "href": image_href, "placement": "break", "align": "center",
    })

    for label, value in (
        ("time-start", "0"),
        ("time-end", row.get("time_end", "")),
        ("freq-start", "0"),
        ("freq-end", row.get("freq_end", "")),
    ):
        r = ET.SubElement(tbody, "row")
        ET.SubElement(r, "entry").text = label
        ET.SubElement(r, "entry").text = value

    related = ET.SubElement(topic, "related-links")
    ET.SubElement(related, "link", {"href": "../gram-index.dita", "format": "dita"})

    topic_path.write_text(_serialise(topic), encoding="utf-8", newline="\n")
    return [topic_path] + ([copied] if copied is not None else [])


def emit_analysis_topic(row: dict, out_dir: Path, image_root: Path) -> list[Path]:
    """Write ``gram_NN_analysis.dita`` for an analysis-typed row plus its asset."""
    gram_num = _gram_num(row["gram_id"])
    topic_id = f"gram_{gram_num}_analysis"
    topic_dir = _topic_dir_for_row(out_dir, row)
    topic_dir.mkdir(parents=True, exist_ok=True)
    topic_path = topic_dir / row["topic_filename"]

    href, copied = copy_asset(
        row.get("png_path", ""), image_root, topic_dir,
    )

    topic = ET.Element("topic", {"id": topic_id, "audience": "-trainee"})
    title = ET.SubElement(topic, "title")
    title.text = f"Gram {gram_num} Analysis"
    body = ET.SubElement(topic, "body")
    section = ET.SubElement(body, "section")
    ET.SubElement(section, "image", {
        "href": href, "placement": "break", "align": "center",
    })
    related = ET.SubElement(topic, "related-links")
    ET.SubElement(related, "link", {"href": "../gram-index.dita", "format": "dita"})

    topic_path.write_text(_serialise(topic), encoding="utf-8", newline="\n")
    return [topic_path] + ([copied] if copied is not None else [])


def emit_wav_stub_topic(row: dict, out_dir: Path, image_root: Path) -> list[Path]:
    """Write the GAPS-Lite stub topic for a ``wav_treatment="gaps-lite"`` row plus its WAV."""
    gram_num = _gram_num(row["gram_id"])
    seq = row["sequence"]
    topic_id = f"gram_{gram_num}_lofar{seq}"
    topic_dir = _topic_dir_for_row(out_dir, row)
    topic_dir.mkdir(parents=True, exist_ok=True)
    topic_path = topic_dir / row["topic_filename"]

    # ``png_path`` is preferred — the extractor resolves it against
    # ``--image-root`` so the generator can copy it without further
    # path arithmetic. ``link_href`` is the raw URI from the PPTX and
    # is kept as a fallback for older CSVs.
    wav_relpath = row.get("png_path", "") or row.get("link_href", "") or row.get("glc_path", "")
    wav_href, copied = copy_asset(wav_relpath, image_root, topic_dir)

    topic = ET.Element("topic", {"id": topic_id})
    title = ET.SubElement(topic, "title")
    title.text = f"Gram {gram_num}"
    if row.get("vessel_name"):
        ph = ET.SubElement(title, "ph", {"audience": "-trainee"})
        ph.text = f" - {row['vessel_name']}"

    body = ET.SubElement(topic, "body")
    section = ET.SubElement(body, "section")
    note = ET.SubElement(section, "note")
    note.text = "This gram requires GAPS-Lite playback."
    p = ET.SubElement(section, "p")
    xref = ET.SubElement(p, "xref", {
        "href": wav_href, "format": "wav", "scope": "local",
    })
    xref.text = row.get("display_text", "") or wav_href

    related = ET.SubElement(topic, "related-links")
    ET.SubElement(related, "link", {"href": "../gram-index.dita", "format": "dita"})

    leading = "<!-- MANUAL REVIEW: GAPS-Lite required -->\n"
    topic_path.write_text(_serialise(topic, leading=leading), encoding="utf-8", newline="\n")
    return [topic_path] + ([copied] if copied is not None else [])


# -----------------------------------------------------------------------------
# Dispatcher (R8)
# -----------------------------------------------------------------------------

@dataclass
class EmitResult:
    written: list[Path]
    skipped: list[dict]
    errors: int


def dispatch_row(row: dict, out_dir: Path, image_root: Path) -> tuple[list[Path], dict | None]:
    """Branch on ``topic_type`` and ``wav_treatment``. Returns ``(written, skipped)``."""
    topic_type = row.get("topic_type", "")
    treatment = (row.get("wav_treatment") or "").strip().lower()
    link_href = row.get("link_href", "") or ""
    is_wav_link = (not row.get("glc_path")) and (link_href.lower().endswith(".wav") or bool(treatment))

    if topic_type == "analysis":
        return (emit_analysis_topic(row, out_dir, image_root), None)

    if topic_type == "glc":
        if treatment == "gaps-lite":
            return (emit_wav_stub_topic(row, out_dir, image_root), None)
        if treatment == "screenshot":
            return (emit_glc_topic(row, out_dir, image_root), None)
        if treatment == "":
            # No WAV treatment, no glc_path -> empty WAV row, skip.
            if is_wav_link:
                LOGGER.error(
                    "Skipping row %s/%s/%s seq=%s: wav_treatment is empty",
                    row["publication"], row["gram_id"], row["topic_type"], row["sequence"],
                )
                return ([], _skip_record(row, "wav_treatment is empty"))
            return (emit_glc_topic(row, out_dir, image_root), None)
        if treatment == "tbd":
            LOGGER.error(
                "Skipping row %s/%s/%s seq=%s: wav_treatment is TBD",
                row["publication"], row["gram_id"], row["topic_type"], row["sequence"],
            )
            return ([], _skip_record(row, "wav_treatment is TBD"))
        # Any other unknown treatment.
        LOGGER.error(
            "Skipping row %s/%s/%s seq=%s: unknown wav_treatment %r",
            row["publication"], row["gram_id"], row["topic_type"], row["sequence"], treatment,
        )
        return ([], _skip_record(row, f"unknown wav_treatment {treatment!r}"))

    LOGGER.error("Skipping row with unknown topic_type %r", topic_type)
    return ([], _skip_record(row, f"unknown topic_type {topic_type!r}"))


def _skip_record(row: dict, reason: str) -> dict:
    return {
        "publication": row["publication"],
        "chapter": row.get("chapter", ""),
        "gram_id": row["gram_id"],
        "topic_type": row["topic_type"],
        "sequence": row["sequence"],
        "reason": reason,
    }


# -----------------------------------------------------------------------------
# Ditamaps (FR-012)
# -----------------------------------------------------------------------------

def emit_main_ditamap(rows: list[dict], out_dir: Path) -> Path:
    """Write ``ditamaps/main.ditamap`` with ``<topichead>`` per chapter."""
    ditamap_dir = out_dir / "ditamaps"
    ditamap_dir.mkdir(parents=True, exist_ok=True)
    map_path = ditamap_dir / "main.ditamap"

    chapters: OrderedDict[str, tuple[str, list[dict]]] = OrderedDict()
    for row in rows:
        if row["publication"] != "main":
            continue
        chapter_title = row.get("chapter", "") or ""
        slug = slugify(chapter_title)
        key = slug
        if key not in chapters:
            chapters[key] = (chapter_title, [])
        chapters[key][1].append(row)

    root = ET.Element("map", {"title": "Main"})
    for slug, (title, chapter_rows) in chapters.items():
        topichead = ET.SubElement(root, "topichead", {"navtitle": title})
        for row in chapter_rows:
            gram_dir = _gram_folder_name(row["gram_id"])
            href = f"../main/{slug}/{gram_dir}/{row['topic_filename']}"
            ET.SubElement(topichead, "topicref", {"href": href})

    map_path.write_text(_serialise(root), encoding="utf-8", newline="\n")
    return map_path


def emit_test_ditamap(publication: str, rows: list[dict], out_dir: Path) -> Path:
    """Write ``ditamaps/<publication>.ditamap`` flat (no topichead)."""
    ditamap_dir = out_dir / "ditamaps"
    ditamap_dir.mkdir(parents=True, exist_ok=True)
    map_path = ditamap_dir / f"{publication}.ditamap"
    n = publication.removeprefix("progress-test-")
    root = ET.Element("map", {"title": f"Progress Test {n}"})
    for row in rows:
        if row["publication"] != publication:
            continue
        gram_dir = _gram_folder_name(row["gram_id"])
        href = f"../{publication}/{gram_dir}/{row['topic_filename']}"
        ET.SubElement(root, "topicref", {"href": href})
    map_path.write_text(_serialise(root), encoding="utf-8", newline="\n")
    return map_path


# -----------------------------------------------------------------------------
# Reports
# -----------------------------------------------------------------------------

def write_manifest(out_dir: Path, files: list[Path]) -> Path:
    """Write ``manifest.txt`` listing every produced file (sorted)."""
    manifest_path = out_dir / "manifest.txt"
    rels = sorted(p.relative_to(out_dir).as_posix() for p in files)
    manifest_path.write_text("\n".join(rels) + "\n", encoding="utf-8", newline="\n")
    return manifest_path


def write_skipped_report(out_dir: Path, skipped: list[dict]) -> Path | None:
    """Write ``skipped.txt`` only when at least one row was skipped."""
    if not skipped:
        return None
    path = out_dir / "skipped.txt"
    lines: list[str] = []
    for s in skipped:
        lines.append(
            f'publication={s["publication"]} chapter={s.get("chapter", "")} '
            f'gram_id="{s["gram_id"]}" topic_type={s["topic_type"]} '
            f'sequence={s["sequence"]} reason="{s["reason"]}"'
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate DITA from the signed-off CSV")
    parser.add_argument("--csv", required=True, type=Path, dest="csv_path")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--image-root", required=True, type=Path, dest="image_root")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    setup_logging(Path("generate.log"))

    if not args.csv_path.is_file():
        LOGGER.error("CSV does not exist: %s", args.csv_path)
        return 1

    if args.clean and args.out.exists():
        LOGGER.info("Cleaning existing output tree at %s", args.out)
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    try:
        rows = read_csv(args.csv_path)
    except Exception as exc:
        LOGGER.error("Failed to read CSV: %s", exc)
        return 1

    written: list[Path] = []
    skipped: list[dict] = []
    errors = 0
    for row in rows:
        try:
            paths, skip = dispatch_row(row, args.out, args.image_root)
            for path in paths:
                written.append(path)
                LOGGER.info("Wrote %s", path)
            if skip is not None:
                skipped.append(skip)
        except Exception as exc:
            errors += 1
            LOGGER.error("Failed to emit row %s: %s", row, exc)

    publications = sorted({r["publication"] for r in rows})
    ditamap_paths: list[Path] = []
    if any(r["publication"] == "main" for r in rows):
        ditamap_paths.append(emit_main_ditamap(rows, args.out))
        LOGGER.info("Wrote ditamap %s", ditamap_paths[-1])
    for pub in publications:
        if pub.startswith("progress-test-"):
            path = emit_test_ditamap(pub, rows, args.out)
            ditamap_paths.append(path)
            LOGGER.info("Wrote ditamap %s", path)

    manifest_path = write_manifest(args.out, written + ditamap_paths)
    LOGGER.info("Wrote manifest %s", manifest_path)

    skipped_path = write_skipped_report(args.out, skipped)
    if skipped_path is not None:
        LOGGER.info("Wrote skipped report %s", skipped_path)

    LOGGER.info(
        "Generation summary: files=%d ditamaps=%d skipped=%d errors=%d",
        len(written), len(ditamap_paths), len(skipped), errors,
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
