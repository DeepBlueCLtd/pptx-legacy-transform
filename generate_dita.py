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
    "time_end", "freq_end", "png_path", "file_size", "wav_treatment", "warnings",
)

# Optional refactoring-planning columns the extractor now writes. Their
# presence is not required (old CSVs still validate) but when present
# they steer DITA generation per spec 005-style refactor flow.
#
# ``master_png_path`` (feature 006) is read with an empty default and is
# never added to the strict ``CSV_COLUMNS`` required-set, so a CSV without
# it (the current 16-column ``source.csv`` or any legacy CSV) stays valid
# and produces byte-identical output — the deduplication feature is inert
# by default (FR-010, SC-005).
OPTIONAL_CSV_COLUMNS: tuple[str, ...] = (
    "target_doc", "target_chapter", "target_ext", "master_png_path",
)

# The ``@name`` of the DITA ``<data>`` provenance element that flags a
# redirected (deduplicated) lofar and anchors its reversal (feature 006).
ORIGINAL_ASSET_PATH = "original-asset-path"

# XML declaration + OASIS DOCTYPE preambles emitted at the head of every
# generated topic and ditamap. Oxygen identifies a file as DITA by its
# DOCTYPE public ID; without these its DITA Maps Manager rejects a bare
# ``<map>`` ("This file does not appear to be a DITA map") and Author
# will not recognise a bare ``<topic>``. The same constants are mirrored
# in ``publish_html.py`` for DITA-OT's benefit.
TOPIC_DOCTYPE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA Topic//EN" "topic.dtd">\n'
)
MAP_DOCTYPE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">\n'
)

LOGGER = logging.getLogger(__name__)


def _write_text(path: Path, text: str) -> None:
    """Write ``text`` with LF endings, working on Python 3.9.

    ``Path.write_text`` only grew a ``newline`` parameter in 3.10; the
    air-gapped target runs WinPython 3.9, so force LF via ``open`` to
    preserve the byte-identical-output contract.
    """
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


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

def _normalise_gram_id(raw: str) -> str:
    """Canonicalise a ``gram_id`` cell to a plain integer string.

    The CSV stage doubles as the author's refactoring surface — when
    moving grams between chapters/publications they often need to
    renumber to avoid colliding with grams already in the target.
    Keeping the column as a bare integer (``"5"``, ``"12"``) makes
    that affordance obvious in any spreadsheet editor; the author
    types the new number and moves on.

    Legacy forms (``"Gram 5"``, ``"gram-12"``, etc.) are accepted on
    read and folded to the integer form so an older CSV upgrades
    transparently. Values without digits pass through unchanged so
    downstream tooling can still flag them.
    """
    s = (raw or "").strip()
    if not s:
        return s
    digits = re.findall(r"\d+", s)
    if not digits:
        return s
    return str(int(digits[0]))


def read_csv(path: Path) -> list[dict]:
    """Read the intermediate CSV with strict header validation (FR-014).

    ``gram_id`` cells are normalised to the canonical ``"Gram NN"`` form
    so downstream grouping treats ``"12"``, ``"Gram 12"``, and ``"Gram 12 "``
    as the same gram.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        actual = tuple(reader.fieldnames or ())
        missing = [c for c in CSV_COLUMNS if c not in actual]
        if missing:
            raise ValueError(
                f"CSV missing required columns: {missing}\n"
                f"Actual header: {actual}"
            )
        rows: list[dict] = []
        for row in reader:
            row = dict(row)
            row["gram_id"] = _normalise_gram_id(row.get("gram_id", ""))
            rows.append(row)
    return rows


def check_row_identity(rows: list[dict]) -> list[str]:
    """Verify the row-identity tuple is unique across ``rows``.

    Per ``contracts/csv-schema.md`` the unique row key is
    ``(publication, chapter, gram_id, topic_type, sequence)``. Two rows
    sharing that tuple mean two source grams were silently merged at
    the CSV-editing stage — typically a refactor where the author moved
    a gram into a chapter that already had a gram with the same
    ``gram_id`` and forgot to renumber. Without this check the generator
    happily folds both into one topic, dropping the second analysis
    section and interleaving the two grams' GLC sections.

    Returns the list of human-readable error strings (one per
    collision); empty means the CSV is clean. The first occurrence of
    each duplicate tuple is reported as the anchor, so the author can
    decide which side to renumber.
    """
    first_seen: dict[tuple, int] = {}
    errors: list[str] = []
    for line_no, row in enumerate(rows, start=2):  # +1 header, 1-based
        # Identity now includes effective_chapter + effective_doc + the
        # gram's source chapter + vessel name so the same gram_id can
        # coexist across decks / chapters or across distinct grams within
        # a single (chapter, deck) bucket — the collision check fires
        # only when two rows are truly indistinguishable.
        key = (
            row.get("publication", ""), _effective_chapter(row),
            _effective_doc(row), row.get("gram_id", ""),
            row.get("chapter", ""), row.get("vessel_name", ""),
            row.get("topic_type", ""), row.get("sequence", ""),
        )
        if key in first_seen:
            errors.append(
                f"Duplicate row identity at CSV line {line_no} "
                f"(first seen at line {first_seen[key]}): "
                f"publication={key[0]!r} target_chapter={key[1]!r} "
                f"target_doc={key[2]!r} gram_id={key[3]!r} "
                f"chapter={key[4]!r} vessel_name={key[5]!r} "
                f"topic_type={key[6]!r} sequence={key[7]!r}. "
                f"Two source rows are indistinguishable on every field — "
                f"renumber one or amend vessel_name to disambiguate."
            )
        else:
            first_seen[key] = line_no
    return errors


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


def _relpath_posix(target: Path, start_dir: Path) -> str:
    """Return ``target`` as a POSIX path relative to ``start_dir`` (may use ``..``).

    Mirrors the ``os.path.relpath`` branch of ``resolve_image_href`` but for
    two *output* locations: the file a redirected lofar links to (in the
    master gram's folder) and the redirected gram's own folder. Used by the
    deduplication redirect branch (feature 006) so a redirected href is the
    same kind of ``../``-bearing relative path the generator already emits.
    """
    import os
    rel_str = os.path.relpath(
        target.resolve(strict=False), start_dir.resolve(strict=False),
    )
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
    """Return the on-disk numeric segment for ``gram_id``, zero-padded to 2.

    Used to build deterministic, two-digit DITA paths and topic IDs
    (``gram-05/gram_05.dita``, ``id="gram_05"``) regardless of how the
    CSV cell is written — ``"5"``, ``"05"``, or the legacy ``"Gram 05"``
    all resolve to ``"05"``. Three-digit corpora work too (``"123"`` →
    ``"123"``) because the format width is a minimum, not a max.
    """
    digits = re.findall(r"\d+", gram_id)
    if not digits:
        return "00"
    return f"{int(digits[0]):02d}"


def _gram_folder_name(gram_id: str, suffix: str = "") -> str:
    """Return the per-gram folder name, e.g. ``"gram-01"`` or ``"gram-01a"``.

    ``suffix`` disambiguates two grams that legitimately share a
    ``gram_id`` within the same ``(target_chapter, target_doc)`` bucket
    after a CSV-driven refactor (computed by ``_compute_gram_suffixes``).
    """
    return f"gram-{_gram_num(gram_id)}{suffix}"


def _topic_filename(gram_id: str, suffix: str = "") -> str:
    """Return the per-gram topic filename, e.g. ``"gram_01.dita"``."""
    return f"gram_{_gram_num(gram_id)}{suffix}.dita"


def _topic_id(gram_id: str, suffix: str = "") -> str:
    """Return the topic ``id`` attribute, e.g. ``"gram_01"``."""
    return f"gram_{_gram_num(gram_id)}{suffix}"


def _effective_chapter(row: dict) -> str:
    """Chapter the row will land in after refactoring. Falls back to source."""
    return row.get("target_chapter") or row.get("chapter", "")


def _effective_doc(row: dict) -> str:
    """Deck filename the row will land in after refactoring (may be empty)."""
    return row.get("target_doc", "") or ""


def _doc_slug(target_doc: str) -> str:
    """Slugified stem of a target-deck filename for use as a path segment.

    Empty input → empty output, so a missing ``target_doc`` omits the
    deck level from the output path entirely.
    """
    if not target_doc:
        return ""
    return slugify(Path(target_doc).stem)


def _compute_gram_suffixes(rows: list[dict]) -> dict[tuple, str]:
    """Detect gram_id collisions and assign letter suffixes.

    After a CSV refactor a single ``(publication, target_chapter,
    target_doc, gram_id)`` bucket may end up containing two distinct
    grams (e.g. a Week 1 Gram 5 and a Week 2 Gram 5 both moved into the
    same target deck without renumbering). Two grams are treated as
    distinct when they differ on ``(chapter, vessel_name)`` — the
    source chapter the gram came from plus its vessel label.

    Returns a mapping ``{(publication, effective_chapter, effective_doc,
    gram_id, chapter, vessel_name): suffix}`` where ``suffix`` is ``""``
    for grams that don't collide and ``"a"``, ``"b"``, … (first-seen
    order) for those that do.
    """
    # First pass: identities seen per bucket, in first-seen order.
    identities_by_bucket: dict[tuple, list[tuple]] = {}
    for row in rows:
        bucket = (
            row.get("publication", ""),
            _effective_chapter(row),
            _effective_doc(row),
            row.get("gram_id", ""),
        )
        identity = (row.get("chapter", ""), row.get("vessel_name", ""))
        ids = identities_by_bucket.setdefault(bucket, [])
        if identity not in ids:
            ids.append(identity)
    # Second pass: assign a suffix only when a bucket carries >1 identity.
    suffixes: dict[tuple, str] = {}
    for bucket, ids in identities_by_bucket.items():
        if len(ids) <= 1:
            for ident in ids:
                suffixes[bucket + ident] = ""
        else:
            for n, ident in enumerate(ids):
                # 'a', 'b', …, 'z', then 'aa' once we'd run out — letter
                # blocks of 26 are plenty for any plausible CSV.
                suffix = ""
                idx = n
                while True:
                    suffix = chr(ord("a") + (idx % 26)) + suffix
                    idx = idx // 26 - 1
                    if idx < 0:
                        break
                suffixes[bucket + ident] = suffix
    return suffixes


def _suffix_for_row(row: dict, suffixes: dict[tuple, str]) -> str:
    """Lookup helper paired with ``_compute_gram_suffixes``."""
    key = (
        row.get("publication", ""),
        _effective_chapter(row),
        _effective_doc(row),
        row.get("gram_id", ""),
        row.get("chapter", ""),
        row.get("vessel_name", ""),
    )
    return suffixes.get(key, "")


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
    """Return the per-publication root.

    Layout: ``{out}/{pub}/[{doc_slug}/]`` for non-main publications and
    ``{out}/main/{chapter_slug}/[{doc_slug}/]`` for the main pub. The
    ``doc_slug`` segment is only inserted when ``target_doc`` is
    populated, keeping pre-refactor CSVs producing the original layout.
    """
    pub = row["publication"]
    doc_slug = _doc_slug(_effective_doc(row))
    if pub != "main":
        root = out_dir / pub
    else:
        _, _, chapter_slug = _normalise_chapter(_effective_chapter(row))
        root = out_dir / "main" / chapter_slug
    if doc_slug:
        root = root / doc_slug
    return root


def _topic_dir_for_row(out_dir: Path, row: dict, suffix: str = "") -> Path:
    """Return the directory the topic + its asset live in.

    Each gram gets its own sub-directory so the original asset filenames
    can be preserved (slugified) without colliding across grams in the
    same chapter. ``suffix`` is the collision-disambiguation letter
    computed by ``_compute_gram_suffixes`` (empty when the gram doesn't
    collide).
    """
    return _publication_root(out_dir, row) / _gram_folder_name(row["gram_id"], suffix)


# -----------------------------------------------------------------------------
# Large-asset deduplication: master index (feature 006)
# -----------------------------------------------------------------------------

@dataclass
class MasterTarget:
    """Where a redirected lofar links to: the master gram's copy.

    ``topic_dir`` is the master gram's output folder; ``link_basename`` is
    the slugified filename of the asset a redirector links to within it —
    the image for an image lofar, the ``.glc`` for an audio lofar (the link
    target of the ``.glc``/``.wav`` pair, FR-009). See data-model.md Entity 3.
    """

    topic_dir: Path
    link_basename: str


def build_master_index(
    rows: list[dict], out_dir: Path, suffixes: dict[tuple, str],
) -> dict[str, MasterTarget]:
    """Map every non-redirected asset-owning row's ``png_path`` → ``MasterTarget``.

    The **index pass** (feature 006, R4): a redirected row carries the
    master row's ``png_path`` in ``master_png_path``; this index lets the
    emit pass resolve that key to the master's output location and link
    filename. Only non-redirected rows (empty ``master_png_path``) are
    recorded — they are the masters. Rows without a usable asset extension
    are skipped. Building this is pure in-memory work over already-loaded
    rows and emits nothing, so it is inert when no row redirects (FR-010).
    """
    index: dict[str, MasterTarget] = {}
    for row in rows:
        if (row.get("master_png_path", "") or "").strip():
            continue  # redirected row — never itself a master
        png = row.get("png_path", "") or ""
        if not png:
            continue
        asset_suffix = Path(png).suffix.lower()
        if asset_suffix == ".wav":
            glc = row.get("glc_path", "") or ""
            if not glc:
                continue
            link_basename = slugify_asset_name(Path(glc).name)
        elif asset_suffix in (".png", ".jpg", ".jpeg"):
            link_basename = slugify_asset_name(Path(png).name)
        else:
            continue
        suffix = _suffix_for_row(row, suffixes)
        topic_dir = _topic_dir_for_row(out_dir, row, suffix)
        index[png] = MasterTarget(topic_dir, link_basename)
    return index


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


def _serialise(root: ET.Element, doctype: str = "") -> str:
    """Serialise ``root`` to a UTF-8 XML string with LF endings.

    ``doctype`` is an optional preamble (XML declaration + ``<!DOCTYPE>``)
    prepended verbatim — see ``TOPIC_DOCTYPE`` / ``MAP_DOCTYPE``. Oxygen's
    DITA Maps Manager (and Author) classifies a file as DITA by its DOCTYPE
    public ID; without it a bare ``<map>``/``<topic>`` is rejected with
    "This file does not appear to be a DITA map". The preamble is therefore
    emitted into the source tree rather than only injected at publish time.

    Output is pretty-printed for human review while preserving mixed-content
    elements (titles, paragraphs with inline phrases) byte-for-byte.
    """
    _pretty_indent(root)
    body = ET.tostring(root, encoding="unicode")
    # ElementTree uses self-closing for empty elements; that matches the
    # contract examples (e.g. <image .../>, <link .../>).
    return f"{doctype}{body}\n"


def _append_provenance_data(section: ET.Element, original_path: str) -> None:
    """Append the redirected-lofar provenance ``<data>`` element (feature 006).

    Emitted as the **last** child of a redirected lofar ``<section>``:
    ``<data name="original-asset-path" value="…"/>``. Its presence alone
    flags the lofar as redirected (FR-007) and anchors reversal (FR-008);
    ``<data>`` is part of the standard DITA metadata domain (DTD-valid, no
    specialisation) and is suppressed from default trainee XHTML (FR-006).
    ``value`` is the original local path of the **link target** — the row's
    ``png_path`` for an image lofar, its ``glc_path`` for an audio lofar
    (never the ``.wav``).
    """
    ET.SubElement(section, "data", {
        "name": ORIGINAL_ASSET_PATH, "value": original_path,
    })


def _append_gramframe_table(
    parent: ET.Element, image_href: str, time_end: str, freq_end: str,
    display_text: str = "",
) -> ET.Element:
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
    section = ET.SubElement(parent, "section", {"outputclass": "lofar-stage"})
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
    return section


def _append_analysis_section(
    parent: ET.Element, href: str,
) -> None:
    """Append the instructor-only analysis-sheet section.

    DOCX assets are linked via ``<xref>`` (the trainee opens them in
    Word); PNG assets are embedded inline as ``<image>``. The section
    carries ``audience="-trainee"`` so the trainee profile elides the
    analysis sheet entirely.
    """
    section = ET.SubElement(parent, "section", {
        "audience": "-trainee", "outputclass": "analysis-sheet",
    })
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
) -> ET.Element:
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
    section = ET.SubElement(parent, "section", {"outputclass": "lofar-stage"})
    if display_text:
        ET.SubElement(section, "title").text = display_text
    p = ET.SubElement(section, "p")
    xref = ET.SubElement(p, "xref", {
        "href": glc_href, "format": "glc", "scope": "local",
    })
    xref.text = display_text or glc_href
    return section


def emit_gram_topic(
    gram_rows: list[dict], out_dir: Path, image_root: Path,
    suffix: str = "", master_index: dict[str, MasterTarget] | None = None,
) -> tuple[list[Path], list[dict], int]:
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
    topic_dir = _topic_dir_for_row(out_dir, first, suffix)
    topic_dir.mkdir(parents=True, exist_ok=True)
    topic_path = topic_dir / _topic_filename(first["gram_id"], suffix)

    topic = ET.Element("topic", {"id": _topic_id(first["gram_id"], suffix)})
    title = ET.SubElement(topic, "title")
    title.text = f"Gram {gram_num}{suffix}"
    if first.get("vessel_name"):
        ph = ET.SubElement(title, "ph", {
            "audience": "-trainee", "outputclass": "vessel-name",
        })
        ph.text = f" - {first['vessel_name']}"
    body = ET.SubElement(topic, "body")

    written: list[Path] = []
    skipped: list[dict] = []
    index = master_index or {}
    redirected = 0

    def _resolve_redirect(r: dict) -> MasterTarget | None:
        """Return the master this row redirects to, or ``None``.

        A row is redirected iff ``master_png_path`` is non-empty *and*
        resolves in the master index. A non-empty-but-unresolvable target
        (missing/blank master) is logged as a WARNING and treated as
        non-redirected so the asset is copied locally instead (FR-014).
        """
        key = (r.get("master_png_path", "") or "").strip()
        if not key:
            return None
        target = index.get(key)
        if target is None:
            LOGGER.warning(
                "Redirect target not resolvable for %s/%s/%s seq=%s: "
                "master_png_path=%r not found; copying asset locally instead.",
                r["publication"], r["gram_id"], r["topic_type"],
                r["sequence"], key,
            )
        return target

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
            master = _resolve_redirect(row)
            if master is not None:
                # Redirected: link to the master copy, copy nothing locally,
                # and record the original local path for reversal (feature 006).
                href = _relpath_posix(master.topic_dir / master.link_basename, topic_dir)
                section = _append_gramframe_table(
                    body, href,
                    row.get("time_end", ""), row.get("freq_end", ""),
                    row.get("display_text", ""),
                )
                _append_provenance_data(section, png_path)
                redirected += 1
                continue
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
            master = _resolve_redirect(row)
            if master is not None:
                # Redirected audio pair: link to the master ``.glc`` (FR-009);
                # neither ``.glc`` nor ``.wav`` is copied — the large ``.wav``
                # stays adjacent to the master ``.glc``. Record the ``.glc``
                # link-target path (not the ``.wav``) for an exact inverse.
                glc_href = _relpath_posix(
                    master.topic_dir / master.link_basename, topic_dir,
                )
                section = _append_glc_viewer_link(
                    body, glc_href, row.get("display_text", ""),
                )
                _append_provenance_data(section, glc_path)
                redirected += 1
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

    # Navigation back to the publication index is delivered by the page
    # chrome (a future custom header bar), not by per-topic related-links:
    # the historical ``<related-links>`` pointed at a ``gram-index.dita``
    # that was never generated, producing a 404 in every gram page.

    _write_text(topic_path, _serialise(topic, TOPIC_DOCTYPE))
    return [topic_path] + written, skipped, redirected


# -----------------------------------------------------------------------------
# Dispatcher (R8)
# -----------------------------------------------------------------------------

@dataclass
class EmitResult:
    written: list[Path]
    skipped: list[dict]
    errors: int


def _gram_groups(rows: list[dict]) -> "OrderedDict[tuple, list[dict]]":
    """Group rows into grams, preserving CSV order.

    A "gram" is the rows sharing ``(publication, effective_chapter,
    effective_doc, gram_id, chapter, vessel_name)`` — the same tuple
    used by the suffix map. Including ``chapter`` and ``vessel_name``
    keeps two distinct grams with the same ``gram_id`` (e.g. moved into
    the same target chapter without renumbering) as separate groups
    rather than silently merged.
    """
    groups: OrderedDict[tuple, list[dict]] = OrderedDict()
    for row in rows:
        key = (
            row.get("publication", ""),
            _effective_chapter(row),
            _effective_doc(row),
            row.get("gram_id", ""),
            row.get("chapter", ""),
            row.get("vessel_name", ""),
        )
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


def emit_main_ditamap(
    rows: list[dict], out_dir: Path, suffixes: dict[tuple, str] | None = None,
) -> Path:
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
            sfx = _suffix_for_row(row, suffixes) if suffixes else ""
            doc_slug = _doc_slug(_effective_doc(row))
            gram_dir = _gram_folder_name(row["gram_id"], sfx)
            uniq = f"{doc_slug}/{gram_dir}" if doc_slug else gram_dir
            if uniq in seen:
                continue
            seen.add(uniq)
            topic_file = _topic_filename(row["gram_id"], sfx)
            prefix = f"{doc_slug}/" if doc_slug else ""
            href = f"main/{slug}/{prefix}{gram_dir}/{topic_file}"
            ET.SubElement(topichead, "topicref", {"href": href})

    _write_text(map_path, _serialise(root, MAP_DOCTYPE))
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


def emit_test_ditamap(
    publication: str, rows: list[dict], out_dir: Path,
    suffixes: dict[tuple, str] | None = None,
) -> Path:
    """Write ``<publication>.ditamap`` at the output root, flat (no topichead)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    map_path = out_dir / f"{publication}.ditamap"
    root = ET.Element("map")
    _append_map_title(root, _flat_publication_title(publication))
    seen: set[str] = set()
    for row in rows:
        if row["publication"] != publication:
            continue
        sfx = _suffix_for_row(row, suffixes) if suffixes else ""
        doc_slug = _doc_slug(_effective_doc(row))
        gram_dir = _gram_folder_name(row["gram_id"], sfx)
        uniq = f"{doc_slug}/{gram_dir}" if doc_slug else gram_dir
        if uniq in seen:
            continue
        seen.add(uniq)
        topic_file = _topic_filename(row["gram_id"], sfx)
        prefix = f"{doc_slug}/" if doc_slug else ""
        href = f"{publication}/{prefix}{gram_dir}/{topic_file}"
        ET.SubElement(root, "topicref", {"href": href})
    _write_text(map_path, _serialise(root, MAP_DOCTYPE))
    return map_path


# -----------------------------------------------------------------------------
# Reports
# -----------------------------------------------------------------------------

TRAINEE_DITAVAL = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<val>\n'
    '  <prop att="audience" val="-trainee" action="exclude"/>\n'
    '</val>\n'
)


def write_trainee_ditaval(out_dir: Path) -> Path:
    """Emit the DITAVAL profile that the student edition filters with.

    DITA elements authored for instructor-only content carry
    ``audience="-trainee"``; ``publish_html.py`` requires this file to
    exist next to the ditamaps and refuses to build otherwise.
    """
    path = out_dir / "trainee.ditaval"
    _write_text(path, TRAINEE_DITAVAL)
    return path


def write_manifest(out_dir: Path, files: list[Path]) -> Path:
    """Write ``manifest.txt`` listing every produced file (sorted)."""
    manifest_path = out_dir / "manifest.txt"
    rels = sorted(p.relative_to(out_dir).as_posix() for p in files)
    _write_text(manifest_path, "\n".join(rels) + "\n")
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
    _write_text(path, "\n".join(lines) + "\n")
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

    duplicates = check_row_identity(rows)
    if duplicates:
        for msg in duplicates:
            LOGGER.error(msg)
        LOGGER.error(
            "Aborting before emission: %d duplicate row identit%s detected.",
            len(duplicates), "y" if len(duplicates) == 1 else "ies",
        )
        return 1

    written: list[Path] = []
    skipped: list[dict] = []
    errors = 0
    redirected_total = 0
    suffixes = _compute_gram_suffixes(rows)
    # Index pass (feature 006): map each master row's png_path to its output
    # location so redirected rows can link to it. Inert when no row redirects.
    master_index = build_master_index(rows, args.out, suffixes)
    for key, gram_rows in _gram_groups(rows).items():
        try:
            suffix = suffixes.get(key, "")
            paths, skips, redirected = emit_gram_topic(
                gram_rows, args.out, args.image_root, suffix=suffix,
                master_index=master_index,
            )
            for path in paths:
                written.append(path)
                LOGGER.info("Wrote %s", path)
            skipped.extend(skips)
            redirected_total += redirected
        except Exception as exc:
            errors += 1
            LOGGER.error("Failed to emit gram %s: %s", key, exc)

    publications = sorted({r["publication"] for r in rows})
    ditamap_paths: list[Path] = []
    if any(r["publication"] == "main" for r in rows):
        ditamap_paths.append(emit_main_ditamap(rows, args.out, suffixes))
        LOGGER.info("Wrote ditamap %s", ditamap_paths[-1])
    for pub in publications:
        if pub != "main":
            path = emit_test_ditamap(pub, rows, args.out, suffixes)
            ditamap_paths.append(path)
            LOGGER.info("Wrote ditamap %s", path)

    ditaval_path = write_trainee_ditaval(args.out)
    LOGGER.info("Wrote DITAVAL profile %s", ditaval_path)

    manifest_path = write_manifest(args.out, written + ditamap_paths + [ditaval_path])
    LOGGER.info("Wrote manifest %s", manifest_path)

    skipped_path = write_skipped_report(args.out, skipped)
    if skipped_path is not None:
        LOGGER.info("Wrote skipped report %s", skipped_path)

    LOGGER.info(
        "Generation summary: files=%d ditamaps=%d skipped=%d redirected=%d errors=%d",
        len(written), len(ditamap_paths), len(skipped), redirected_total, errors,
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    rc = main()
    # Preserve CLI exit codes when invoked as a script, but stay silent
    # when invoked from an interactive REPL via runpy.run_path —
    # ``sys.exit`` would otherwise kill the interpreter and break the
    # up-arrow iteration loop. ``sys.ps1`` is only defined in
    # interactive sessions.
    if rc and not hasattr(sys, "ps1"):
        sys.exit(rc)
