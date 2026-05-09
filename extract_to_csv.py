"""Extractor (User Story 2): walk a content tree and emit the intermediate CSV.

Stage 2 of the migration pipeline. Walks every ``.pptx`` under the
configured input root, classifies each as ``main`` or
``progress-test-N`` by filename pattern (R2), opens each via
``python-pptx``, and writes one CSV row per resulting DITA topic
(R11, contracts/csv-schema.md). The shape-grouping step itself is the
documented ``NotImplementedError`` stub mandated by FR-015 and R1; every
piece of surrounding infrastructure is fully implemented so the rest of
the team can write tests against it before the stub is replaced.

Logging follows R10: dual stdout + ``extract.log``, three levels
(INFO/WARNING/ERROR), no silent exception swallowing (FR-014).
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Iterable, Iterator

from pptx import Presentation


CSV_COLUMNS: tuple[str, ...] = (
    "publication", "chapter", "gram_id", "vessel_name", "topic_type",
    "sequence", "topic_filename", "display_text", "glc_path", "time_end",
    "freq_end", "png_path", "wav_treatment", "warnings",
)

DEFAULT_TEST_PATTERN: str = "progress_test"

LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Logging convention (R10) -- mirrored in generate_dita.py.
# -----------------------------------------------------------------------------

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
# GLC parser (R6, contracts/glc-schema.md)
# -----------------------------------------------------------------------------

@dataclass
class GlcDocument:
    image_filename: str = ""
    time_end: str = ""
    freq_end: str = ""
    warnings: list[str] = field(default_factory=list)


def parse_glc(path: Path) -> GlcDocument:
    """Parse a GLC XML file tolerantly. Never raises.

    Per contracts/glc-schema.md: missing elements yield empty values plus
    a verbatim warning string; malformed XML yields an empty result with
    a single ``"GLC malformed: <reason>"`` warning. Path stripping uses
    ``pathlib.PureWindowsPath(raw).name`` so a Windows ``W:\\foo\\bar.PNG``
    surfaces as ``bar.PNG``.
    """
    doc = GlcDocument()
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        first = str(exc).splitlines()[0] if str(exc) else "unknown error"
        doc.warnings.append(f"GLC malformed: {first}")
        return doc
    except OSError as exc:
        doc.warnings.append(f"GLC malformed: {exc}")
        return doc

    root = tree.getroot()

    filenames = root.findall("data_source/filename")
    if not filenames:
        doc.warnings.append("GLC missing filename")
    else:
        if len(filenames) > 1:
            doc.warnings.append("GLC duplicate filename")
        raw = (filenames[0].text or "").strip()
        if not raw:
            doc.warnings.append("GLC missing filename")
            doc.image_filename = ""
        else:
            doc.image_filename = PureWindowsPath(raw).name

    bottom = root.findtext("data_source/bitmap_crop_values/bottom_crop")
    if bottom is None or not bottom.strip():
        doc.warnings.append("GLC missing bottom_crop")
        doc.time_end = ""
    else:
        doc.time_end = bottom.strip()

    bandwidth = root.findtext("settings/lofar/bandwidth")
    if bandwidth is None or not bandwidth.strip():
        doc.warnings.append("GLC missing bandwidth")
        doc.freq_end = ""
    else:
        doc.freq_end = bandwidth.strip()

    return doc


# -----------------------------------------------------------------------------
# Path resolution and walking
# -----------------------------------------------------------------------------

def resolve_glc_path(href: str, content_root: Path, source_dir: Path | None = None) -> Path | None:
    """Resolve a GLC href against the per-gram or per-ten-grams layout (FR-006).

    Returns ``None`` and logs a WARNING when the file cannot be found.
    """
    if not href:
        LOGGER.warning("GLC not found: empty href")
        return None
    rel = Path(href.replace("\\", "/"))
    candidates: list[Path] = []
    if source_dir is not None:
        candidates.append((source_dir / rel).resolve(strict=False))
    candidates.append((content_root / rel).resolve(strict=False))
    candidates.append((content_root / rel.name).resolve(strict=False))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    LOGGER.warning("GLC not found: %s", href)
    return None


def walk_pptxs(input_root: Path) -> Iterator[Path]:
    """Yield every ``.pptx`` under ``input_root`` in deterministic sorted order."""
    yield from sorted(input_root.rglob("*.pptx"))


# -----------------------------------------------------------------------------
# Slug + chapter helpers (R3)
# -----------------------------------------------------------------------------

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lower-case, ASCII-only, hyphen-separated slug with collapsed runs."""
    ascii_only = text.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_NON_ALNUM.sub("-", ascii_only).strip("-")
    return slug


def classify_publication(
    pptx: Path,
    test_pattern: str,
    allocated: dict[str, int],
) -> tuple[str, str | None, str | None]:
    """Return ``(publication, chapter, chapter_slug)`` per R2/R3.

    Progress-test PPTXs are detected by case-insensitive substring match
    against the filename. Test numbering is allocated stably in the order
    callers request previously-unseen test PPTXs.
    """
    name = pptx.name.lower()
    if test_pattern.lower() in name:
        if pptx.stem not in allocated:
            allocated[pptx.stem] = len(allocated) + 1
        return (f"progress-test-{allocated[pptx.stem]}", None, None)
    chapter_title = pptx.parent.name
    return ("main", chapter_title, slugify(chapter_title))


# -----------------------------------------------------------------------------
# Shape grouping stub (FR-015 / R1)
# -----------------------------------------------------------------------------

@dataclass
class GlcLink:
    display_text: str
    href: str


@dataclass
class GramPlaceholder:
    gram_id: str
    vessel_name: str
    png_href: str | None
    glc_links: list[GlcLink]


def extract_grams_from_slide(slide, slide_num: int) -> list[GramPlaceholder]:
    """Return the gram placeholders on ``slide`` (currently a documented stub).

    NOT YET IMPLEMENTED. Replacement requires the introspection report
    (User Story 3) against a real instructor PPTX to answer:

      1. Is the analysis-PNG hyperlink attached at the shape level on
         every gram, or does it sometimes ride on a text run?
      2. Does the link text box always sit immediately below its title
         rectangle, and is "immediately below" measured in EMUs or in a
         layout-relative coordinate system?
      3. Are the title and link-box shapes reliably named (e.g.
         "Rectangle 12") or do real authors rename them ad hoc?
      4. Is spatial proximity (top/left distance) sufficient to pair a
         title with its link box, or are there overlap/edge cases?
      5. Are some grams wrapped in GROUP shapes (shape_type=6) that need
         to be expanded before the grouping logic can match them?

    Until that report has been produced, raising explicitly is safer
    than silently producing partial CSV output that the technical author
    would have to undo on the air-gapped network.
    """
    raise NotImplementedError(
        "Shape grouping is not implemented yet. Run introspection against a real "
        "instructor PPTX (see introspect_pptx.py) and use the report to answer "
        "the five questions in this docstring before replacing the stub."
    )


# -----------------------------------------------------------------------------
# Row construction
# -----------------------------------------------------------------------------

def _gram_num_from_id(gram_id: str) -> str:
    digits = re.findall(r"\d+", gram_id)
    return digits[0] if digits else "00"


def gram_to_rows(
    gram: GramPlaceholder,
    publication: str,
    chapter: str | None,
    chapter_slug: str | None,
    content_root: Path,
    source_dir: Path,
) -> list[dict]:
    """Expand one gram into N+1 CSV rows (N GLC links + 1 analysis row)."""
    rows: list[dict] = []
    gram_num = _gram_num_from_id(gram.gram_id)

    for i, link in enumerate(gram.glc_links, start=1):
        warnings: list[str] = []
        href = link.href
        is_wav = href.lower().endswith(".wav")
        glc_path = ""
        time_end = ""
        freq_end = ""
        png_path = ""
        wav_treatment = ""
        display_text = link.display_text
        if is_wav:
            wav_treatment = ""
            warnings.append("WAV link; treatment required")
        else:
            resolved = resolve_glc_path(href, content_root, source_dir=source_dir)
            if resolved is None:
                warnings.append("GLC not found")
                glc_path = href
            else:
                glc_path = str(resolved.relative_to(content_root)) if resolved.is_relative_to(content_root) else str(resolved)
                glc = parse_glc(resolved)
                warnings.extend(glc.warnings)
                time_end = glc.time_end
                freq_end = glc.freq_end
                if glc.image_filename:
                    png_path = glc.image_filename

        rows.append({
            "publication": publication,
            "chapter": chapter or "",
            "gram_id": gram.gram_id,
            "vessel_name": gram.vessel_name,
            "topic_type": "glc",
            "sequence": str(i),
            "topic_filename": f"gram_{gram_num}_lofar{i}.dita",
            "display_text": display_text,
            "glc_path": glc_path,
            "time_end": time_end,
            "freq_end": freq_end,
            "png_path": png_path,
            "wav_treatment": wav_treatment,
            "warnings": ", ".join(warnings),
        })

    analysis_warnings: list[str] = []
    analysis_png = gram.png_href or ""
    if not analysis_png:
        analysis_warnings.append("missing analysis PNG hyperlink")
    rows.append({
        "publication": publication,
        "chapter": chapter or "",
        "gram_id": gram.gram_id,
        "vessel_name": gram.vessel_name,
        "topic_type": "analysis",
        "sequence": "1",
        "topic_filename": f"gram_{gram_num}_analysis.dita",
        "display_text": "",
        "glc_path": "",
        "time_end": "",
        "freq_end": "",
        "png_path": analysis_png,
        "wav_treatment": "",
        "warnings": ", ".join(analysis_warnings),
    })
    return rows


# -----------------------------------------------------------------------------
# CSV writer (R11)
# -----------------------------------------------------------------------------

def write_csv(rows: list[dict], out: Path) -> None:
    """Write rows to a UTF-8-with-BOM, CRLF, QUOTE_MINIMAL CSV."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=list(CSV_COLUMNS),
            quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract PPTX content into the intermediate CSV")
    parser.add_argument("--input-root", required=True, type=Path, dest="input_root")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--test-pattern", default=DEFAULT_TEST_PATTERN, dest="test_pattern")
    args = parser.parse_args(list(argv) if argv is not None else None)

    setup_logging(Path("extract.log"))

    if not args.input_root.is_dir():
        LOGGER.error("Input root does not exist or is not a directory: %s", args.input_root)
        return 1

    rows: list[dict] = []
    pptx_count = 0
    warning_counter: Counter[str] = Counter()
    allocated: dict[str, int] = {}

    try:
        for pptx in walk_pptxs(args.input_root):
            pptx_count += 1
            LOGGER.info("Processing PPTX %s", pptx)
            publication, chapter, chapter_slug = classify_publication(pptx, args.test_pattern, allocated)
            try:
                prs = Presentation(pptx)
            except Exception as exc:
                LOGGER.error("Cannot open PPTX %s: %s", pptx, exc)
                return 1
            for slide_num, slide in enumerate(prs.slides, start=1):
                if slide_num == 1:
                    continue  # welcome slide
                grams = extract_grams_from_slide(slide, slide_num)
                for gram in grams:
                    gram_rows = gram_to_rows(
                        gram, publication, chapter, chapter_slug,
                        args.input_root, source_dir=pptx.parent,
                    )
                    rows.extend(gram_rows)
                    for r in gram_rows:
                        if r["warnings"]:
                            for w in r["warnings"].split(", "):
                                warning_counter[w] += 1
    except NotImplementedError as exc:
        LOGGER.error("Shape grouping stub reached: %s", exc)
        # Still write whatever rows were collected before the stub fired.
        write_csv(rows, args.out)
        return 1

    write_csv(rows, args.out)

    distinct = ", ".join(f"{w}={c}" for w, c in sorted(warning_counter.items()))
    LOGGER.info(
        "Extraction summary: pptx=%d rows=%d warnings=%d distinct=[%s]",
        pptx_count, len(rows), sum(warning_counter.values()), distinct,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
