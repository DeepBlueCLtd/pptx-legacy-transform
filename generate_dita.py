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


_INSTRUCTOR_PREFIX_RE = re.compile(r"^(Instructor )", re.IGNORECASE)


def _normalise_chapter(raw: str) -> tuple[str | None, str, str]:
    """Split an "Instructor "-prefixed chapter name and compute its slug.

    Returns ``(audience_prefix, display_remainder, slug)`` where the
    prefix is wrapped in ``<ph audience="-trainee">`` at emit time so
    the student edition's trainee filter strips it, leaving the
    display-remainder as the visible chapter navtitle.

    The slug is computed from the *remainder* only, so the chapter
    folder name in the DITA source tree never contains the substring
    "instructor" (case-insensitive). Both editions render the same
    chapter at the same path below their edition segment (FR-014,
    FR-016).

    Examples:

    >>> _normalise_chapter("Instructor Week 1 Grams")
    ('Instructor ', 'Week 1 Grams', 'week-1-grams')
    >>> _normalise_chapter("Instructor Pub10_Ed22B_Updated")
    ('Instructor ', 'Pub10_Ed22B_Updated', 'pub10-ed22b-updated')
    >>> _normalise_chapter("Plain Chapter Without Prefix")
    (None, 'Plain Chapter Without Prefix', 'plain-chapter-without-prefix')
    >>> _normalise_chapter("")
    (None, '', '')
    """
    match = _INSTRUCTOR_PREFIX_RE.match(raw)
    if match is None:
        return None, raw, slugify(raw)
    prefix = match.group(1)
    remainder = raw[len(prefix):]
    return prefix, remainder, slugify(remainder)


def _publication_root(out_dir: Path, row: dict) -> Path:
    """Return the per-publication root, ``{out}/{pub}`` or ``{out}/main/{chapter}``."""
    pub = row["publication"]
    if pub != "main":
        return out_dir / pub
    _, _, chapter_slug = _normalise_chapter(row.get("chapter", ""))
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

def _pretty_indent(elem: ET.Element, level: int = 0, indent: str = "  ") -> None:
    """Indent ``elem`` in place, preserving mixed-content elements verbatim.

    A mixed-content element — one whose ``text`` or whose children's ``tail``
    carry non-whitespace characters — is left untouched (its children are
    still descended into so any nested block elements get indented). This
    keeps DITA titles like ``<title>Gram 34<ph> - FR Reliant</ph></title>``
    byte-stable while still pretty-printing the block structure around them.
    """
    children = list(elem)
    if not children:
        return
    has_text = bool(elem.text and elem.text.strip())
    has_inline_tail = any(c.tail and c.tail.strip() for c in children)
    if has_text or has_inline_tail:
        for child in children:
            _pretty_indent(child, level + 1, indent)
        return
    inner_pad = "\n" + indent * (level + 1)
    closing_pad = "\n" + indent * level
    elem.text = inner_pad
    for child in children:
        _pretty_indent(child, level + 1, indent)
        child.tail = inner_pad
    children[-1].tail = closing_pad


def _serialise(root: ET.Element) -> str:
    """Serialise ``root`` to a UTF-8 XML string with LF endings, no preamble.

    Output is pretty-printed for human review while preserving mixed-content
    elements (titles, paragraphs with inline phrases) byte-for-byte.
    """
    _pretty_indent(root)
    body = ET.tostring(root, encoding="unicode")
    # ElementTree uses self-closing for empty elements; that matches the
    # contract examples (e.g. <image .../>, <link .../>).
    return f"{body}\n"


def _append_gramframe_table(
    parent: ET.Element, image_href: str, time_end: str, freq_end: str,
    display_text: str = "",
) -> None:
    """Append one ``<section>`` containing a GramFrame ``gram-config`` table.

    The HTML produced by DITA-OT carries ``class="gram-config"`` on the
    table; the GramFrame browser bundle (``gramframe.bundle.js``) auto-
    detects this class on ``DOMContentLoaded`` and rewrites the table
    into an interactive spectrogram view. See
    ``specs/001-pptx-dita-migration/contracts/gramframe.md``.

    The two named ``<colspec>`` elements are required so DITA-OT emits
    ``colspan="2"`` on the image row — without them the image cell
    renders with ``colspan="1"`` and GramFrame rejects the table.

    When ``display_text`` is supplied (the link label from the source
    PPTX, e.g. ``"Lofar 1"``), a ``<title>`` is emitted inside the
    section so multi-gram pages get a clear heading per spectrogram.
    """
    section = ET.SubElement(parent, "section")
    if display_text:
        ET.SubElement(section, "title").text = display_text
    table = ET.SubElement(section, "table", {"outputclass": "gram-config"})
    tgroup = ET.SubElement(table, "tgroup", {"cols": "2"})
    ET.SubElement(tgroup, "colspec", {"colname": "c1", "colnum": "1"})
    ET.SubElement(tgroup, "colspec", {"colname": "c2", "colnum": "2"})
    tbody = ET.SubElement(tgroup, "tbody")
    image_row = ET.SubElement(tbody, "row")
    image_entry = ET.SubElement(image_row, "entry", {"namest": "c1", "nameend": "c2"})
    ET.SubElement(image_entry, "image", {
        "href": image_href, "placement": "break", "align": "center",
    })
    for label, value in (
        ("time-start", "0"),
        ("time-end", time_end),
        ("freq-start", "0"),
        ("freq-end", freq_end),
    ):
        r = ET.SubElement(tbody, "row")
        ET.SubElement(r, "entry").text = label
        ET.SubElement(r, "entry").text = value


def _append_analysis_section(
    parent: ET.Element, href: str,
) -> None:
    """Append the instructor-only analysis-sheet section.

    DOCX assets are linked via ``<xref>`` (the trainee opens them in
    Word); PNG assets are embedded inline as ``<image>``. The section
    carries ``audience="-trainee"`` so the trainee profile elides the
    analysis sheet entirely.
    """
    section = ET.SubElement(parent, "section", {"audience": "-trainee"})
    title = ET.SubElement(section, "title")
    title.text = "Analysis Sheet"
    if not href:
        return
    suffix = Path(href).suffix.lower().lstrip(".")
    if suffix == "png":
        ET.SubElement(section, "image", {
            "href": href, "placement": "break", "align": "center",
        })
    else:
        p = ET.SubElement(section, "p")
        xref = ET.SubElement(p, "xref", {
            "href": href, "format": suffix or "html", "scope": "local",
        })
        xref.text = "Analysis Sheet"


def _append_glc_viewer_link(
    parent: ET.Element, glc_href: str, display_text: str,
) -> None:
    """Append a GLC-viewer link block (§1.3) to the gram body.

    Emitted instead of a GramFrame table when the GLC's inner
    ``data_source/filename`` is a ``.wav``: there is no pre-rendered
    spectrogram to embed, so the gram page links to the ``.glc`` itself
    and the on-PC GLC viewer reads the file and resolves the adjacent
    ``.wav`` for live aural analysis. The companion ``.wav`` is copied
    next to the ``.glc`` by the caller.

    When ``display_text`` is supplied (the link label from the source
    PPTX), a ``<title>`` is emitted inside the section so multi-gram
    pages get a clear heading per audio link.
    """
    section = ET.SubElement(parent, "section")
    if display_text:
        ET.SubElement(section, "title").text = display_text
    p = ET.SubElement(section, "p")
    xref = ET.SubElement(p, "xref", {
        "href": glc_href, "format": "glc", "scope": "local",
    })
    xref.text = display_text or glc_href


def emit_gram_topic(
    gram_rows: list[dict], out_dir: Path, image_root: Path,
) -> tuple[list[Path], list[dict]]:
    """Write a single ``gram_NN.dita`` carrying every block for one gram.

    The body contains, in order:

    1. The analysis-sheet section (DOCX link or embedded PNG), once,
       wrapped with ``audience="-trainee"``.
    2. One block per ``topic_type="glc"`` row, in CSV ``sequence``
       order. The block shape is chosen by the extension of the asset
       named inside the ``.glc`` (carried through as ``png_path``):

       - ``.png`` / ``.jpg`` → GramFrame ``gram-config`` table
         embedding the image (`dita-topic-schema.md` §1.2). This is
         the shape `gramframe.bundle.js` recognises.
       - ``.wav`` → an ``<xref>`` linking to the ``.glc`` itself
         (§1.3); both the ``.glc`` and the named ``.wav`` are copied
         into the per-gram folder so the on-PC GLC viewer can find
         the audio when a student opens the link.

    Rows whose ``png_path`` is empty or carries any other extension
    are skipped with a warning recorded in ``skipped.txt``.
    """
    analysis_rows = [r for r in gram_rows if r["topic_type"] == "analysis"]
    glc_rows = [r for r in gram_rows if r["topic_type"] == "glc"]
    glc_rows.sort(key=lambda r: int(r["sequence"]) if r["sequence"].isdigit() else 0)

    first = analysis_rows[0] if analysis_rows else glc_rows[0]
    gram_num = _gram_num(first["gram_id"])
    topic_dir = _topic_dir_for_row(out_dir, first)
    topic_dir.mkdir(parents=True, exist_ok=True)
    topic_path = topic_dir / first["topic_filename"]

    topic = ET.Element("topic", {"id": f"gram_{gram_num}"})
    title = ET.SubElement(topic, "title")
    title.text = f"Gram {gram_num}"
    if first.get("vessel_name"):
        ph = ET.SubElement(title, "ph", {"audience": "-trainee"})
        ph.text = f" - {first['vessel_name']}"
    body = ET.SubElement(topic, "body")

    written: list[Path] = []
    skipped: list[dict] = []

    if analysis_rows:
        analysis_row = analysis_rows[0]
        href, copied = copy_asset(
            analysis_row.get("png_path", ""), image_root, topic_dir,
        )
        if copied is not None:
            written.append(copied)
        _append_analysis_section(body, href)

    for row in glc_rows:
        png_path = row.get("png_path", "") or ""
        asset_suffix = Path(png_path).suffix.lower()

        if asset_suffix in (".png", ".jpg", ".jpeg"):
            image_href, copied = copy_asset(png_path, image_root, topic_dir)
            if copied is not None:
                written.append(copied)
            _append_gramframe_table(
                body, image_href,
                row.get("time_end", ""), row.get("freq_end", ""),
                row.get("display_text", ""),
            )
            continue

        if asset_suffix == ".wav":
            glc_path = row.get("glc_path", "") or ""
            if not glc_path:
                reason = "wav-typed GLC row has no glc_path to link to"
                LOGGER.error(
                    "Skipping row %s/%s/%s seq=%s: %s",
                    row["publication"], row["gram_id"], row["topic_type"],
                    row["sequence"], reason,
                )
                skipped.append(_skip_record(row, reason))
                continue
            glc_href, glc_copied = copy_asset(glc_path, image_root, topic_dir)
            wav_href, wav_copied = copy_asset(png_path, image_root, topic_dir)
            if glc_copied is not None:
                written.append(glc_copied)
            if wav_copied is not None:
                written.append(wav_copied)
            _append_glc_viewer_link(body, glc_href, row.get("display_text", ""))
            continue

        if not png_path:
            reason = "png_path missing"
        else:
            reason = f"unsupported asset extension {asset_suffix!r}"
        LOGGER.error(
            "Skipping row %s/%s/%s seq=%s: %s",
            row["publication"], row["gram_id"], row["topic_type"],
            row["sequence"], reason,
        )
        skipped.append(_skip_record(row, reason))

    related = ET.SubElement(topic, "related-links")
    ET.SubElement(related, "link", {"href": "../gram-index.dita", "format": "dita"})

    topic_path.write_text(_serialise(topic), encoding="utf-8", newline="\n")
    return [topic_path] + written, skipped


# -----------------------------------------------------------------------------
# Dispatcher (R8)
# -----------------------------------------------------------------------------

@dataclass
class EmitResult:
    written: list[Path]
    skipped: list[dict]
    errors: int


def _gram_groups(rows: list[dict]) -> "OrderedDict[tuple[str, str, str], list[dict]]":
    """Group rows by ``(publication, chapter, gram_id)`` preserving CSV order."""
    groups: OrderedDict[tuple[str, str, str], list[dict]] = OrderedDict()
    for row in rows:
        key = (row["publication"], row.get("chapter", ""), row["gram_id"])
        groups.setdefault(key, []).append(row)
    return groups


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

def _append_map_title(root: ET.Element, base_title: str) -> None:
    """Append ``<title>{base_title}<ph audience="-trainee"> — Instructor Version</ph></title>``.

    The audience-tagged suffix means the trainee filter renders just
    ``base_title``; the unfiltered (instructor) build renders the
    full decorated form. The ``<title>`` *child* element replaces the
    legacy ``title=`` attribute on ``<map>`` so inline markup can carry
    the audience tag.
    """
    title = ET.SubElement(root, "title")
    title.text = base_title
    ph = ET.SubElement(title, "ph", {"audience": "-trainee"})
    ph.text = " — Instructor Version"


def _append_chapter_navtitle(topichead: ET.Element, raw_chapter: str) -> None:
    """Append ``<topicmeta><navtitle>…</navtitle></topicmeta>`` to ``topichead``.

    The visible text is decomposed by ``_normalise_chapter``. When the
    raw chapter name began with "Instructor " (case-insensitive), the
    prefix is emitted inside ``<ph audience="-trainee">`` so the
    trainee filter strips it; otherwise the navtitle is plain text
    with no ``<ph>`` wrapper.

    The ``<topicmeta>/<navtitle>`` *child* element replaces the legacy
    ``navtitle=`` attribute on ``<topichead>`` so inline markup can
    carry the audience tag.
    """
    audience_prefix, display_remainder, _ = _normalise_chapter(raw_chapter)
    topicmeta = ET.SubElement(topichead, "topicmeta")
    navtitle = ET.SubElement(topicmeta, "navtitle")
    if audience_prefix is None:
        navtitle.text = display_remainder
    else:
        ph = ET.SubElement(navtitle, "ph", {"audience": "-trainee"})
        ph.text = audience_prefix
        ph.tail = display_remainder


def emit_main_ditamap(rows: list[dict], out_dir: Path) -> Path:
    """Write ``main.ditamap`` at the output root with ``<topichead>`` per chapter."""
    out_dir.mkdir(parents=True, exist_ok=True)
    map_path = out_dir / "main.ditamap"

    chapters: OrderedDict[str, tuple[str, list[dict]]] = OrderedDict()
    for row in rows:
        if row["publication"] != "main":
            continue
        chapter_title = row.get("chapter", "") or ""
        _, _, slug = _normalise_chapter(chapter_title)
        key = slug
        if key not in chapters:
            chapters[key] = (chapter_title, [])
        chapters[key][1].append(row)

    root = ET.Element("map")
    _append_map_title(root, "Main")
    for slug, (title, chapter_rows) in chapters.items():
        topichead = ET.SubElement(root, "topichead")
        _append_chapter_navtitle(topichead, title)
        seen: set[str] = set()
        for row in chapter_rows:
            gram_dir = _gram_folder_name(row["gram_id"])
            if gram_dir in seen:
                continue
            seen.add(gram_dir)
            href = f"main/{slug}/{gram_dir}/{row['topic_filename']}"
            ET.SubElement(topichead, "topicref", {"href": href})

    map_path.write_text(_serialise(root), encoding="utf-8", newline="\n")
    return map_path


def _flat_publication_title(publication: str) -> str:
    """Human-readable map title for a non-``main`` (flat) publication.

    ``progress-test-N`` → ``"Progress Test N"`` (preserves the legacy
    title style from feature 001). Any other slug is title-cased with
    hyphens turned into spaces (e.g. ``progress-final-assessment`` →
    ``"Progress Final Assessment"``). This is what gets emitted into
    the ditamap's ``<title>`` child element; the audience-tagged
    " — Instructor Version" suffix is appended by ``_append_map_title``.
    """
    if publication.startswith("progress-test-"):
        n = publication.removeprefix("progress-test-")
        return f"Progress Test {n}"
    return publication.replace("-", " ").title()


def emit_test_ditamap(publication: str, rows: list[dict], out_dir: Path) -> Path:
    """Write ``<publication>.ditamap`` at the output root, flat (no topichead)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    map_path = out_dir / f"{publication}.ditamap"
    root = ET.Element("map")
    _append_map_title(root, _flat_publication_title(publication))
    seen: set[str] = set()
    for row in rows:
        if row["publication"] != publication:
            continue
        gram_dir = _gram_folder_name(row["gram_id"])
        if gram_dir in seen:
            continue
        seen.add(gram_dir)
        href = f"{publication}/{gram_dir}/{row['topic_filename']}"
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
    for key, gram_rows in _gram_groups(rows).items():
        try:
            paths, skips = emit_gram_topic(gram_rows, args.out, args.image_root)
            for path in paths:
                written.append(path)
                LOGGER.info("Wrote %s", path)
            skipped.extend(skips)
        except Exception as exc:
            errors += 1
            LOGGER.error("Failed to emit gram %s: %s", key, exc)

    publications = sorted({r["publication"] for r in rows})
    ditamap_paths: list[Path] = []
    if any(r["publication"] == "main" for r in rows):
        ditamap_paths.append(emit_main_ditamap(rows, args.out))
        LOGGER.info("Wrote ditamap %s", ditamap_paths[-1])
    for pub in publications:
        if pub != "main":
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
