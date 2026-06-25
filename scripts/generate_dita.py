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
    "time_end", "bandwidth", "bandcentre", "png_path", "file_size", "wav_treatment", "warnings",
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
    "target_gram_id",
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

# Common static pages (feature 010): topics shared by every publication,
# copied into each publication folder and referenced as the first ditamap
# entries — ahead of the "Grams" nav folder. Welcome leads, Security second;
# any further top-level ``*.dita`` under the static root follow alphabetically.
STATIC_PAGE_ORDER: tuple[str, ...] = ("welcome.dita", "security.dita")

# Navtitle of the <topichead> that demotes the per-gram topicrefs out of the
# ditamap root into a single nav entry (feature 010).
GRAMS_NAVTITLE = "Grams"

# Hidden, instructor-only per-page edition marker. The trainee DITAVAL strips
# audience="-trainee", so this element survives only in the *instructor* build;
# its outputclass surfaces it as ``<p class="edition-instructor">`` in the
# rendered HTML. A single shared stylesheet keys the Oxygen WebHelp search box
# (and the classification banner) off it — present means instructor, absent
# means student — so both transformation scenarios can run the *same*
# publishing template instead of a student-only variant whose only job is to
# hide the (useless) search box. The class name only ever appears in instructor
# output, so it never trips the student "no instructor" leakage check (SC-002).
EDITION_MARKER_OUTPUTCLASS = "edition-instructor"

# The same per-page marker doubles as GramFrame's persistence opt-in (GramFrame
# >= v0.1.10). On every save/load GramFrame calls
# ``document.getElementById("gf-persistent")``: when that element is present it
# treats the page as the *trainer* (instructor) context and persists spectrogram
# annotations to ``localStorage`` (survives reloads); when absent it falls back
# to ``sessionStorage`` (cleared when the tab closes). We render the id as the
# HTML ``id`` of the audience="-trainee" edition marker, so it survives only in
# the instructor build — instructor annotations persist, student annotations
# stay ephemeral — riding the exact same DITAVAL profiling, no new element. See
# ``specs/001-pptx-dita-migration/contracts/gramframe.md`` §6.
GF_PERSISTENT_MARKER_ID = "gf-persistent"

# Topic body-group open tags into which a static page's edition marker is
# inserted (string surgery, so the author's formatting is preserved elsewhere).
_STATIC_BODY_OPEN_RE = re.compile(
    r"<(?:body|conbody|taskbody|refbody|glossbody)\b[^>]*>"
)

LOGGER = logging.getLogger(__name__)

# Optional testing aid: when set via ``--stub-wav``, every .wav copy in
# ``copy_asset`` is sourced from this path instead of the real file.
# Keeps the DITA tree slim for transit during cross-network testing.
_STUB_WAV_PATH: "Path | None" = None


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
# Trust boundary: fail-fast on our own artifacts (constitution VII)
# -----------------------------------------------------------------------------
#
# Be ruthless with data this pipeline produces and forbids editing; stay
# forgiving only at the boundary with input we do not control (the legacy
# .pptx corpus, the .glc files) and with uncertain *author* judgement (those
# are warned-and-deferred per Principle IV, not crashed). A blank value in one
# of *our* required identity columns, or in a field whose emptiness would
# silently corrupt one of our own invariants, is a defect in our pipeline — so
# we fail loud at the point of use rather than coercing it to "".

class PipelineDataError(Exception):
    """A blank/missing Zone-A required field in an artifact we produced.

    Raised by ``require_field``. Distinct from the warn-and-defer treatment of
    uncertain *source* data (constitution Principle IV): this is our own bug to
    fix, so it aborts the run loudly instead of silently emitting a malformed
    topic. See constitution VII ("Strict on Self-Authored Data").
    """


def require_field(row: dict, field: str, *, line_no: int | None = None) -> str:
    """Return ``row[field]`` stripped, hard-failing if absent or blank.

    For the CSV identity columns (``csv-schema.md`` marks them *Empty allowed?
    = no*: ``publication``, ``gram_id``, ``topic_type``, ``sequence``,
    ``topic_filename``) and for any value promoted to Zone A because an empty
    one would break our own logic (the ``.wav`` dedup view fields). These are
    data our extractor produces and the author must not edit, so a blank one is
    a pipeline defect we fail loud on (constitution VII) — not the messy
    *source* value that ``copy_asset`` dangles or that Principle IV defers.
    """
    value = (row.get(field) or "").strip()
    if value:
        return value
    where = f" at CSV line {line_no}" if line_no is not None else ""
    raise PipelineDataError(
        f"Required field {field!r} is missing or blank{where} "
        f"(publication={row.get('publication', '')!r}, "
        f"gram_id={row.get('gram_id', '')!r}, "
        f"topic_type={row.get('topic_type', '')!r}, "
        f"sequence={row.get('sequence', '')!r}). This is identity data our "
        f"own pipeline produces and must never be empty — fix the offending "
        f"row rather than leaving the cell blank (constitution VII)."
    )


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
    first_seen: dict[tuple, tuple[int, dict]] = {}
    errors: list[str] = []
    for line_no, row in enumerate(rows, start=2):  # +1 header, 1-based
        # The key is the path the gram lands at: publication + effective
        # chapter + effective doc + effective gram number + topic_type +
        # sequence. Two rows sharing it mean two distinct grams resolve to
        # the same week + number without renumbering (feature 008) — the
        # generator would otherwise silently merge them into one topic.
        #
        # The identity columns are Zone-A data our extractor produces and the
        # author must not edit (constitution VII): a blank one builds a key
        # with an empty component that silently collides, so we fail loud here
        # rather than coerce to "". (``read_csv`` guarantees the columns are
        # *present*; ``require_field`` guards their *values*.) ``gram_id`` is
        # required too — validated explicitly since it reaches the key via
        # ``_effective_gram_id``.
        require_field(row, "gram_id", line_no=line_no)
        key = (
            require_field(row, "publication", line_no=line_no),
            _effective_chapter(row),
            _effective_doc(row), _gram_num(_effective_gram_id(row)),
            require_field(row, "topic_type", line_no=line_no),
            require_field(row, "sequence", line_no=line_no),
        )
        if key in first_seen:
            anchor_line, anchor = first_seen[key]
            errors.append(
                f"Duplicate gram slot at CSV line {line_no} "
                f"(first seen at line {anchor_line}): "
                f"publication={key[0]!r} effective_chapter={key[1]!r} "
                f"effective_doc={key[2]!r} gram_number={key[3]!r} "
                f"topic_type={key[4]!r} sequence={key[5]!r}. "
                f"Two distinct grams "
                f"(gram_id={anchor.get('gram_id', '')!r} from chapter="
                f"{anchor.get('chapter', '')!r} vs gram_id="
                f"{row.get('gram_id', '')!r} from chapter="
                f"{row.get('chapter', '')!r}) resolve to the same week + "
                f"number — run deduplicate_csv.py to renumber the collision."
            )
        else:
            first_seen[key] = (line_no, row)
    return errors


def check_main_chapter_assigned(rows: list[dict]) -> list[str]:
    """Verify every ``main`` row resolves to a week (a non-empty chapter slug).

    Since the week folders are pulled up to the top level of the main
    ditamap (replacing the single ``Grams`` folder), a ``main`` row with no
    effective chapter has no week sub-document to nest under — its gram would
    sit naked at the map root, flooding the nav. A no-week ``main`` deck
    (e.g. Pub10, whose ``target_chapter`` an analyst hasn't filled in yet)
    is therefore a fail-fast error: the analyst must assign the week before
    final emission, exactly as an un-renumbered collision must be deduped.

    The effective chapter is ``target_chapter`` else ``chapter`` (feature
    008); ``_normalise_chapter`` yields an empty slug only when that value is
    blank (or punctuation/whitespace-only). Returns the list of
    human-readable error strings (one per offending row); empty means every
    ``main`` row is assigned a week.
    """
    errors: list[str] = []
    for line_no, row in enumerate(rows, start=2):  # +1 header, 1-based
        if row.get("publication", "") != "main":
            continue
        eff_chapter = _effective_chapter(row)
        _, _, slug = _normalise_chapter(eff_chapter)
        if not slug:
            errors.append(
                f"Unassigned week on main row at CSV line {line_no}: "
                f"gram_id={row.get('gram_id', '')!r} from "
                f"chapter={row.get('chapter', '')!r} has a blank effective "
                f"chapter (target_chapter={row.get('target_chapter', '')!r}). "
                f"Fill in target_chapter with the week number so the gram "
                f"lands under a Week folder."
            )
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
    # Testing aid: when --stub-wav is set, every .wav copy is sourced from
    # the stub file but keeps its slugified per-gram filename so the
    # paired .glc's internal `data_source/filename` reference still
    # resolves at publish time. Keeps gramframe functional with a silent
    # stub and slims the DITA tree for transit between systems.
    if _STUB_WAV_PATH is not None and source.suffix.lower() == ".wav":
        source = _STUB_WAV_PATH
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


def _gram_folder_name(gram_id: str) -> str:
    """Return the per-gram folder name, e.g. ``"gram-01"``."""
    return f"gram-{_gram_num(gram_id)}"


def _topic_filename(gram_id: str) -> str:
    """Return the per-gram topic filename, e.g. ``"gram_01.dita"``."""
    return f"gram_{_gram_num(gram_id)}.dita"


def _topic_id(gram_id: str) -> str:
    """Return the topic ``id`` attribute, e.g. ``"gram_01"``."""
    return f"gram_{_gram_num(gram_id)}"


def _effective_gram_id(row: dict) -> str:
    """The gram number the row lands at: ``target_gram_id`` else ``gram_id``.

    Feature 008: when several source decks fold into one week folder, the
    dedupe step renumbers colliding grams into the optional ``target_gram_id``
    column. The generator derives every per-gram name (folder, topic filename,
    topic id, ``Gram NN`` title) from this effective value so a renumbered gram
    gets a clean, unique path; ``gram_id`` is preserved as provenance.
    """
    return (row.get("target_gram_id", "") or "").strip() or row.get("gram_id", "")


def _effective_chapter(row: dict) -> str:
    """Chapter the row will land in after refactoring. Falls back to source."""
    return row.get("target_chapter") or row.get("chapter", "")


def _effective_doc(row: dict) -> str:
    """Deck filename the row will land in after refactoring — always empty.

    No publication carries a per-document folder tier. ``main`` is flat at
    ``main/week-N/gram-NN/``; every **non-main** publication
    (``progress-test-N``, ``final-assessment-N``) is allocated per source-deck
    stem in ``classify_publication``, so each maps to exactly **one** deck and a
    ``doc`` tier could never disambiguate two decks — it only ever added a
    redundant folder echoing the publication name (e.g.
    ``progress-test-1/instructor-progress-test-1-grams/``).

    Forcing the effective doc to ``""`` for **all** publications keeps the topic
    path, the ditamap href, and the ``check_row_identity`` collision key
    consistently doc-less in one place. The CSV's ``target_doc`` column is now
    ignored here (deprecated like ``wav_treatment``, retained only for
    round-trip compatibility), so a stray value never reintroduces the tier.
    """
    return ""


def _doc_slug(target_doc: str) -> str:
    """Slugified stem of a target-deck filename for use as a path segment.

    Empty input → empty output, so a missing ``target_doc`` omits the
    deck level from the output path entirely.
    """
    if not target_doc:
        return ""
    return slugify(Path(target_doc).stem)


_INSTRUCTOR_PREFIX_RE = re.compile(r"^(Instructor )", re.IGNORECASE)
_WEEK_NUMBER_RE = re.compile(r"^\d+$")


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

    A bare-integer chapter ``N`` (feature 008's four-week ``main`` IA) expands
    to display ``Week N`` and slug ``week-N`` — the editable ``target_chapter``
    holds the terse week number, expanded only at emit time.

    Examples:

    >>> _normalise_chapter("Instructor Week 1 Grams")
    ('Instructor ', 'Week 1 Grams', 'week-1-grams')
    >>> _normalise_chapter("Instructor Pub10_Ed22B_Updated")
    ('Instructor ', 'Pub10_Ed22B_Updated', 'pub10-ed22b-updated')
    >>> _normalise_chapter("2")
    (None, 'Week 2', 'week-2')
    >>> _normalise_chapter("Plain Chapter Without Prefix")
    (None, 'Plain Chapter Without Prefix', 'plain-chapter-without-prefix')
    >>> _normalise_chapter("")
    (None, '', '')
    """
    if _WEEK_NUMBER_RE.match(raw):
        week = str(int(raw))  # strip any leading zeros
        return None, f"Week {week}", f"week-{week}"
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


def _topic_dir_for_row(out_dir: Path, row: dict) -> Path:
    """Return the directory the topic + its asset live in.

    Each gram gets its own sub-directory so the original asset filenames
    can be preserved (slugified) without colliding across grams in the
    same chapter. The folder is named from the *effective* gram number
    (``target_gram_id`` else ``gram_id``), so a renumbered gram (feature
    007) lands at its clean, unique ``gram-NN`` path.
    """
    return _publication_root(out_dir, row) / _gram_folder_name(_effective_gram_id(row))


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


def _master_index_key(png_path: str, asset_suffix: str, row: dict) -> tuple:
    """Master-index key for an asset-owning row or for its redirector.

    Audio rows are keyed by view as well as path (issue #78): a redirected
    ``.wav`` row links to the *master's* ``.glc``, so it must resolve only
    to a master presenting the same ``(time_end, bandwidth, bandcentre)``
    window — ``deduplicate_csv.py`` only pairs rows whose views match, so
    building the lookup key from the redirector's own values makes key
    equality exactly view equality (and lets two masters share one ``.wav``
    path with different views). The frequency view is the band pair
    ``(bandwidth, bandcentre)`` (issue #87): two grams with equal bandwidth
    but a different band centre are genuinely different views. Image
    redirects stay path-only: the row's own time/freq ride in its
    gram-config table, so byte-identical images are interchangeable across
    views.
    """
    if asset_suffix == ".wav":
        # Promotion clause (constitution VII): for a ``.wav`` row these three
        # view fields *are* the dedup key — an empty one silently mis-pairs two
        # genuinely different audio views, corrupting our own logic. So even
        # though the values originate in the external ``.glc`` (nominally
        # forgiving), a blank on a ``.wav`` row is a defect we fail loud on.
        # Analysis/image/GLC-missing rows never reach this branch, so their
        # legitimately-empty views are unaffected.
        return ("wav", png_path,
                require_field(row, "time_end"),
                require_field(row, "bandwidth"),
                require_field(row, "bandcentre"))
    return ("img", png_path)


def build_master_index(
    rows: list[dict], out_dir: Path,
) -> dict[tuple, MasterTarget]:
    """Map every non-redirected asset-owning row's index key → ``MasterTarget``.

    The **index pass** (feature 006, R4): a redirected row carries the
    master row's ``png_path`` in ``master_png_path``; this index lets the
    emit pass resolve that key (combined with the redirector's own view
    for ``.wav`` rows — see ``_master_index_key``) to the master's output
    location and link filename. Only non-redirected rows (empty
    ``master_png_path``) are recorded — they are the masters. Rows without
    a usable asset extension are skipped. Building this is pure in-memory
    work over already-loaded rows and emits nothing, so it is inert when
    no row redirects (FR-010).
    """
    index: dict[tuple, MasterTarget] = {}
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
        elif asset_suffix in (".png", ".jpg", ".jpeg", ".gif"):
            link_basename = slugify_asset_name(Path(png).name)
        else:
            continue
        topic_dir = _topic_dir_for_row(out_dir, row)
        index[_master_index_key(png, asset_suffix, row)] = MasterTarget(
            topic_dir, link_basename,
        )
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


def _parse_freq_num(value: str) -> float | None:
    """Parse a numeric frequency string, or ``None`` when blank/non-numeric."""
    try:
        return float((value or "").strip())
    except (TypeError, ValueError):
        return None


def _format_freq_num(value: float) -> str:
    """Format a frequency value deterministically.

    Integer-valued results render with no decimal point (``400``, ``0``);
    non-integer results (from an odd ``bandwidth``) render with trailing
    zeros stripped (``200.5``). Keeps output stable for the determinism diff.
    """
    if value == int(value):
        return str(int(value))
    return ("%f" % value).rstrip("0").rstrip(".")


def _derive_freq_band(bandwidth: str, bandcentre: str) -> tuple[str, str]:
    """Derive ``(freq_start, freq_end)`` from a band's width and centre (issue #87).

    The band spans ``bandwidth/2`` either side of ``bandcentre``:
    ``freq_start = bandcentre - bandwidth/2``, ``freq_end = bandcentre +
    bandwidth/2``. Degrades gracefully (research R3): a blank/non-numeric
    ``bandcentre`` falls back to the legacy interpretation (band starts at
    zero, ends at ``bandwidth`` — i.e. ``bandcentre == bandwidth/2``); a
    blank/non-numeric ``bandwidth`` yields blank limits rather than crashing.
    """
    bw = _parse_freq_num(bandwidth)
    if bw is None:
        return "", ""
    bc = _parse_freq_num(bandcentre)
    if bc is None:
        return "0", _format_freq_num(bw)
    half = bw / 2
    return _format_freq_num(bc - half), _format_freq_num(bc + half)


def _append_gramframe_table(
    parent: ET.Element, image_href: str, time_end: str,
    bandwidth: str, bandcentre: str,
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
    freq_start, freq_end = _derive_freq_band(bandwidth, bandcentre)
    for label, value in (
        ("time-start", "0"),
        ("time-end", time_end),
        ("freq-start", freq_start),
        ("freq-end", freq_end),
    ):
        r = ET.SubElement(tbody, "row")
        ET.SubElement(r, "entry").text = label
        ET.SubElement(r, "entry").text = value
    return section


# Stable id on the analysis-sheet section so the instructor-only floating
# jump link (issue #91) can target it with an in-page ``<xref>``.
ANALYSIS_SECTION_ID = "analysis-sheet"


def _append_edition_marker(body: ET.Element) -> None:
    """Prepend the hidden instructor-only edition marker as the first child of a
    topic body, so every rendered page carries the per-edition signal the shared
    stylesheet reads (see ``EDITION_MARKER_OUTPUTCLASS``). The empty ``<p>``
    renders nothing useful on its own — the theme hides ``.edition-instructor``
    — its presence/absence is the whole payload.

    The marker's HTML ``id`` (``gf-persistent``) is also GramFrame's persistence
    opt-in: present only in the instructor build, it makes GramFrame persist this
    page's spectrogram annotations to ``localStorage`` (see
    ``GF_PERSISTENT_MARKER_ID``).
    """
    body.insert(0, ET.Element("p", {
        "audience": "-trainee", "outputclass": EDITION_MARKER_OUTPUTCLASS,
        "id": GF_PERSISTENT_MARKER_ID,
    }))


def _inject_static_edition_marker(text: str, source: Path) -> str:
    """Return *text* (a static DITA page) with the instructor-only edition
    marker inserted as the first child of its topic body.

    String surgery (not an XML round-trip) keeps the author's formatting
    byte-for-byte everywhere except the one inserted line. A page with no
    recognised body-group element is returned unchanged with a warning — its
    rendered page then can't drive the shared edition stylesheet, but
    generation still succeeds (graceful degradation).
    """
    marker = (
        f'\n    <p audience="-trainee" id="{GF_PERSISTENT_MARKER_ID}" '
        f'outputclass="{EDITION_MARKER_OUTPUTCLASS}"/>'
    )
    new_text, count = _STATIC_BODY_OPEN_RE.subn(
        lambda m: m.group(0) + marker, text, count=1,
    )
    if count == 0:
        LOGGER.warning(
            "Static page %s has no topic body; edition marker not stamped "
            "(its page can't drive the shared edition stylesheet).", source,
        )
        return text
    return new_text


def _append_analysis_jump_link(parent: ET.Element, topic_id: str) -> None:
    """Append the instructor-only floating "jump to Analysis Sheet" link.

    Issue #91: on a long gram page the instructor wants to reach the
    analysis image fast from anywhere. We emit a single in-page
    ``<xref>`` (rendered ``<p class="analysis-jump">`` → a fixed pill by
    the theme CSS) that scrolls to the analysis-sheet section. The link
    carries ``audience="-trainee"`` so the trainee profile elides it
    entirely — both the link and its target are instructor-only, so the
    student edition never ships a dangling anchor.
    """
    p = ET.SubElement(parent, "p", {
        "audience": "-trainee", "outputclass": "analysis-jump",
    })
    xref = ET.SubElement(p, "xref", {
        "href": f"#{topic_id}/{ANALYSIS_SECTION_ID}",
    })
    xref.text = "Analysis Sheet"


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
        "id": ANALYSIS_SECTION_ID,
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
    master_index: dict[tuple, MasterTarget] | None = None,
) -> tuple[list[Path], list[dict], int]:
    """Write a single ``gram_NN.dita`` carrying every block for one gram.

    The body contains, in order:

    1. The analysis-sheet section (DOCX link or embedded PNG), once,
       wrapped with ``audience="-trainee"``.
    2. One block per ``topic_type="glc"`` row, in CSV ``sequence``
       order. The block shape is chosen by the extension of the asset
       named inside the ``.glc`` (carried through as ``png_path``):

       - ``.png`` / ``.jpg`` / ``.gif`` → GramFrame ``gram-config`` table
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
    eff_gram_id = _effective_gram_id(first)
    gram_num = _gram_num(eff_gram_id)
    topic_dir = _topic_dir_for_row(out_dir, first)
    topic_dir.mkdir(parents=True, exist_ok=True)
    topic_path = topic_dir / _topic_filename(eff_gram_id)

    topic_id = _topic_id(eff_gram_id)
    topic = ET.Element("topic", {"id": topic_id})
    title = ET.SubElement(topic, "title")
    title.text = f"Gram {gram_num}"
    if first.get("vessel_name"):
        ph = ET.SubElement(title, "ph", {
            "audience": "-trainee", "outputclass": "vessel-name",
        })
        ph.text = f" - {first['vessel_name']}"
    body = ET.SubElement(topic, "body")
    _append_edition_marker(body)

    written: list[Path] = []
    skipped: list[dict] = []
    index = master_index or {}
    redirected = 0

    def _resolve_redirect(r: dict) -> MasterTarget | None:
        """Return the master this row redirects to, or ``None``.

        A row is redirected iff ``master_png_path`` is non-empty *and*
        resolves in the master index. For a ``.wav`` row the lookup key
        also carries the row's own ``(time_end, bandwidth, bandcentre)``
        view, so the redirect only resolves to a master whose ``.glc``
        presents the same window (issue #78, #87). A non-empty-but-unresolvable target
        (missing/blank master, or no master with the matching view) is
        logged as a WARNING and treated as non-redirected so the asset is
        copied locally instead (FR-014).
        """
        key = (r.get("master_png_path", "") or "").strip()
        if not key:
            return None
        suffix = Path(r.get("png_path", "") or "").suffix.lower()
        target = index.get(_master_index_key(key, suffix, r))
        if target is None:
            LOGGER.warning(
                "Redirect target not resolvable for %s/%s/%s seq=%s: "
                "master_png_path=%r %s; copying asset locally instead.",
                r["publication"], r["gram_id"], r["topic_type"],
                r["sequence"], key,
                "has no master row with a matching (time_end, bandwidth, bandcentre) view"
                if suffix == ".wav" else "not found",
            )
        return target

    if analysis_rows:
        analysis_row = analysis_rows[0]
        href, copied = copy_asset(
            analysis_row.get("png_path", ""), image_root, topic_dir,
        )
        if copied is not None:
            written.append(copied)
        _append_analysis_jump_link(body, topic_id)
        _append_analysis_section(body, href)

    for row in glc_rows:
        png_path = row.get("png_path", "") or ""
        asset_suffix = Path(png_path).suffix.lower()

        if asset_suffix in (".png", ".jpg", ".jpeg", ".gif"):
            master = _resolve_redirect(row)
            if master is not None:
                # Redirected: link to the master copy, copy nothing locally,
                # and record the original local path for reversal (feature 006).
                href = _relpath_posix(master.topic_dir / master.link_basename, topic_dir)
                section = _append_gramframe_table(
                    body, href,
                    row.get("time_end", ""),
                    row.get("bandwidth", ""), row.get("bandcentre", ""),
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
                row.get("time_end", ""),
                row.get("bandwidth", ""), row.get("bandcentre", ""),
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
    effective_doc, effective_gram_number)`` — the path the gram lands at.
    After the dedupe step renumbers within-week collisions (feature 008),
    distinct grams carry distinct effective numbers, so each forms its own
    group. Any *un-renumbered* collision is caught by ``check_row_identity``
    (which aborts before grouping), so two distinct grams never merge here.
    """
    groups: OrderedDict[tuple, list[dict]] = OrderedDict()
    for row in rows:
        key = (
            require_field(row, "publication"),  # Zone-A; constitution VII
            _effective_chapter(row),
            _effective_doc(row),
            _gram_num(_effective_gram_id(row)),
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


def _chapter_topic_stem(slug: str) -> str:
    """Topic filename stem (and topic ``id``) for a chapter slug.

    Mirrors the gram convention (folders hyphenated, topic files
    underscored): slug ``week-2`` → stem ``week_2`` → ``week-2/week_2.dita``
    with ``id="week_2"``. Slugs never contain underscores (``slugify`` maps
    every non-alphanumeric run to a hyphen), so the substitution is
    collision-free. A stem that would start with a digit is prefixed so the
    topic ``id`` stays a valid XML ID.
    """
    stem = slug.replace("-", "_")
    if not stem[:1].isalpha():
        stem = f"chapter_{stem}"
    return stem


def emit_main_chapter_topics(rows: list[dict], out_dir: Path) -> list[Path]:
    """Write one chapter topic — a navigable *sub-document* — per effective
    ``main`` chapter, at ``main/<slug>/<stem>.dita``, and return the paths.

    The ditamap nests each week's gram topicrefs under a ``<topicref>`` to
    this topic (not a nav-only ``<topichead>``), so every renderer gives the
    week its own page at the top level of the map — the publication index
    lists the weeks, and each week page lists its grams (DITA-OT and Oxygen
    both auto-generate child links for a topic with topicref children). The
    topic body is intentionally empty: the title is the content, the
    children are the point — apart from the hidden instructor-only edition
    marker, which every page carries so the shared stylesheet can tell the
    editions apart (see ``EDITION_MARKER_OUTPUTCLASS``).

    The title is decomposed by ``_normalise_chapter``: a leading
    "Instructor " (case-insensitive) is wrapped in ``<ph audience="-trainee">``
    so the trainee filter strips it, exactly as the chapter navtitles did.
    Chapterless rows (empty slug) get no chapter topic; ``main`` rejects
    them fail-fast in ``check_main_chapter_assigned`` before this runs.
    """
    written: list[Path] = []
    for slug, (raw_chapter, _) in _main_chapters(rows).items():
        if not slug:
            continue
        audience_prefix, display_remainder, _ = _normalise_chapter(raw_chapter)
        topic = ET.Element("topic", {"id": _chapter_topic_stem(slug)})
        title = ET.SubElement(topic, "title")
        if audience_prefix is None:
            title.text = display_remainder
        else:
            ph = ET.SubElement(title, "ph", {"audience": "-trainee"})
            ph.text = audience_prefix
            ph.tail = display_remainder
        _append_edition_marker(ET.SubElement(topic, "body"))
        chapter_dir = out_dir / "main" / slug
        chapter_dir.mkdir(parents=True, exist_ok=True)
        path = chapter_dir / f"{_chapter_topic_stem(slug)}.dita"
        _write_text(path, _serialise(topic, TOPIC_DOCTYPE))
        written.append(path)
    return written


def discover_static_pages(static_root: Path) -> list[str]:
    """Return the common static page filenames (top-level ``*.dita`` under
    ``static_root``) in nav order: Welcome, Security, then any extras
    alphabetically (feature 010).

    Returns ``[]`` when ``static_root`` is absent or holds no pages, so
    generation degrades gracefully — the ditamaps then carry no shared pages.
    """
    if not static_root.is_dir():
        return []
    names = [p.name for p in static_root.glob("*.dita")]

    def rank(name: str) -> tuple[int, str]:
        try:
            return (STATIC_PAGE_ORDER.index(name), "")
        except ValueError:
            return (len(STATIC_PAGE_ORDER), name)

    return sorted(names, key=rank)


def copy_static_tree(static_root: Path, pub_dir: Path) -> list[Path]:
    """Mirror the ``static_root`` tree into ``pub_dir`` (a per-publication output
    folder), returning the destination paths in a stable order (feature 010).

    The static author keeps each page self-contained with relative hrefs;
    copying the tree verbatim beside the ditamap preserves them — the publish
    stager rewrites only the leading ``<publication>/`` map prefix, never a
    topic-internal href. ``.md`` files (folder docs like README) are skipped.

    Each ``.dita`` page is stamped with the hidden instructor-only edition
    marker (so its rendered page can drive the shared edition stylesheet, like
    every generated topic); the insertion is the only deviation from a verbatim
    copy, and is deterministic. Every other file (images, …) is copied
    byte-for-byte for the determinism contract.
    """
    if not static_root.is_dir():
        return []
    copied: list[Path] = []
    for src in sorted(static_root.rglob("*")):
        if not src.is_file() or src.suffix.lower() == ".md":
            continue
        dst = pub_dir / src.relative_to(static_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() == ".dita":
            _write_text(dst, _inject_static_edition_marker(
                src.read_text(encoding="utf-8"), src,
            ))
        else:
            shutil.copyfile(src, dst)
        copied.append(dst)
    return copied


def _append_static_topicrefs(
    root: ET.Element, static_pages: Iterable[str],
) -> None:
    """Prepend the common static pages as the first top-level ``<topicref>``s.

    Each href is the bare filename: the ditamap lives *inside* its
    publication folder, right beside the copied static pages (feature 010).
    """
    for name in static_pages:
        ET.SubElement(root, "topicref", {"href": name})


def _append_grams_topichead(root: ET.Element) -> ET.Element:
    """Append and return the ``<topichead>`` (navtitle ``Grams``) that holds
    every per-gram topicref, collapsing N gram entries into a single root-level
    nav item (feature 010). Uses the ``<topicmeta>/<navtitle>`` child form,
    matching the chapter topicheads.
    """
    topichead = ET.SubElement(root, "topichead")
    topicmeta = ET.SubElement(topichead, "topicmeta")
    navtitle = ET.SubElement(topicmeta, "navtitle")
    navtitle.text = GRAMS_NAVTITLE
    return topichead


def _main_chapters(rows: list[dict]) -> "OrderedDict[str, tuple[str, list[dict]]]":
    """Group the ``main`` rows by effective-chapter slug, preserving CSV order.

    Chapters are grouped by the *effective* chapter (feature 008: the week
    number a row lands in, ``target_chapter`` else ``chapter``). Maps each
    slug to ``(raw effective chapter, its rows)``; shared by the chapter-topic
    and ditamap emitters so the two always agree on the chapter set.
    """
    chapters: OrderedDict[str, tuple[str, list[dict]]] = OrderedDict()
    for row in rows:
        if row["publication"] != "main":
            continue
        eff_chapter = _effective_chapter(row)
        _, _, slug = _normalise_chapter(eff_chapter)
        if slug not in chapters:
            chapters[slug] = (eff_chapter, [])
        chapters[slug][1].append(row)
    return chapters


def emit_main_ditamap(
    rows: list[dict], out_dir: Path, static_pages: Iterable[str] = (),
) -> Path:
    """Write ``main/main.ditamap`` — inside the publication folder — with one
    chapter-topic ``<topicref>`` per week at the **top level** of the map.

    The map lives beside the content it references, so every href is
    folder-relative (``welcome.dita``, ``week-2/gram-07/gram_07.dita``) and
    the publication folder is self-contained: open the map in Oxygen from
    ``dita/main/`` and publish, no path rewriting required. Nothing is
    written at the output root.

    Each chapter (``Week 1`` … ``Week 4``, per feature 008's effective
    chapter) is a real sub-document pulled **up to the top level** of the
    map (replacing the former single ``Grams`` folder): a ``<topicref>`` to
    the chapter topic written by ``emit_main_chapter_topics``, sitting beside
    the common static pages, with the week's gram topicrefs nested one tier
    below it in ascending gram-number order. (CSV order interleaves decks —
    a week's native grams first, then the even-sliced no-week decks'
    renumbered grams — which read as a jumble when rendered.) So the
    top-level nav reads ``Welcome · Security · Week 1 · Week 2 · …``.

    Every ``main`` row must resolve to a week (a non-empty chapter slug);
    an unassigned chapter is rejected fail-fast upstream by
    ``check_main_chapter_assigned`` before this emitter runs, so no gram
    topicref sits naked at the map root. The defensive ``else`` below keeps
    the emitter structural (flat at root) should it ever be called directly
    with such a row.
    """
    pub_dir = out_dir / "main"
    pub_dir.mkdir(parents=True, exist_ok=True)
    map_path = pub_dir / "main.ditamap"

    root = ET.Element("map")
    _append_map_title(root, "Main")
    _append_static_topicrefs(root, static_pages)
    for slug, (_, chapter_rows) in _main_chapters(rows).items():
        if slug:
            chapter_ref = ET.SubElement(root, "topicref", {
                "href": f"{slug}/{_chapter_topic_stem(slug)}.dita",
            })
        else:
            chapter_ref = root
        seen: set[str] = set()
        gram_refs: list[tuple[int, str]] = []
        for row in chapter_rows:
            doc_slug = _doc_slug(_effective_doc(row))
            gram_dir = _gram_folder_name(_effective_gram_id(row))
            uniq = f"{doc_slug}/{gram_dir}" if doc_slug else gram_dir
            if uniq in seen:
                continue
            seen.add(uniq)
            topic_file = _topic_filename(_effective_gram_id(row))
            # Build the href from non-empty segments only, mirroring the
            # pathlib-based on-disk layout (_publication_root, which drops
            # empty path parts). A bare-integer week gives slug "week-N"; a
            # no-week deck (e.g. Pub10 with a blank target_chapter) gives an
            # EMPTY slug — interpolating it as "{slug}/..." would emit a
            # leading-slash "/..." (absolute) href that DITA-OT cannot
            # resolve, silently dropping the topic under
            # --processing-mode=lax (a 404 in the rendered output).
            # Filtering empties keeps href == path relative to the map.
            href = "/".join([s for s in (slug, doc_slug, gram_dir) if s]
                            + [topic_file])
            gram_refs.append((int(_gram_num(_effective_gram_id(row))), href))
        for _, href in sorted(gram_refs):
            ET.SubElement(chapter_ref, "topicref", {"href": href})

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
    static_pages: Iterable[str] = (),
) -> Path:
    """Write ``<publication>/<publication>.ditamap`` inside the publication
    folder, with folder-relative hrefs (no ``<publication>/`` prefix).

    The common static pages lead (feature 010); the per-gram topicrefs are
    grouped under a single ``<topichead>`` (navtitle ``Grams``) so they sit one
    level below the ditamap root rather than flooding it as direct children,
    in ascending gram-number order regardless of CSV row order.
    """
    pub_dir = out_dir / publication
    pub_dir.mkdir(parents=True, exist_ok=True)
    map_path = pub_dir / f"{publication}.ditamap"
    root = ET.Element("map")
    _append_map_title(root, _flat_publication_title(publication))
    _append_static_topicrefs(root, static_pages)
    grams_head = _append_grams_topichead(root)
    seen: set[str] = set()
    gram_refs: list[tuple[int, str]] = []
    for row in rows:
        if row["publication"] != publication:
            continue
        doc_slug = _doc_slug(_effective_doc(row))
        gram_dir = _gram_folder_name(_effective_gram_id(row))
        uniq = f"{doc_slug}/{gram_dir}" if doc_slug else gram_dir
        if uniq in seen:
            continue
        seen.add(uniq)
        topic_file = _topic_filename(_effective_gram_id(row))
        prefix = f"{doc_slug}/" if doc_slug else ""
        href = f"{prefix}{gram_dir}/{topic_file}"
        gram_refs.append((int(_gram_num(_effective_gram_id(row))), href))
    for _, href in sorted(gram_refs):
        ET.SubElement(grams_head, "topicref", {"href": href})
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
    parser.add_argument(
        "--clean", action="store_true",
        help="Deprecated no-op: the output tree is now always wiped and rebuilt "
             "from scratch. Accepted only so existing wrappers keep parsing.")
    parser.add_argument(
        "--stub-wav", type=Path, dest="stub_wav", default=None,
        help="Testing aid: copy this file in place of every .wav asset "
             "(keeps slugified per-gram filenames so paired .glc references "
             "still resolve). Slims the DITA tree for cross-system transit.")
    parser.add_argument(
        "--static-root", type=Path, dest="static_root", default=Path("static"),
        help="Folder of common static pages (welcome.dita, security.dita, …) "
             "and their image subfolders. Copied verbatim into each publication "
             "folder and referenced as the first ditamap entries, ahead of the "
             "Grams nav folder. Default: ./static. A missing folder yields no "
             "shared pages (a logged warning), not an error.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    setup_logging(Path("generate.log"))

    global _STUB_WAV_PATH
    if args.stub_wav is not None:
        if not args.stub_wav.is_file():
            LOGGER.error("--stub-wav file does not exist: %s", args.stub_wav)
            return 1
        _STUB_WAV_PATH = args.stub_wav.resolve()
        LOGGER.info("Using stub WAV for every .wav copy: %s", _STUB_WAV_PATH)
    else:
        _STUB_WAV_PATH = None

    if not args.csv_path.is_file():
        LOGGER.error("CSV does not exist: %s", args.csv_path)
        return 1

    # Always rebuild the output tree from scratch. Wiping it up-front verifies
    # it isn't locked (e.g. a publication folder open in Oxygen) and guarantees
    # a run can never blend fresh topics with a previous document's leftovers —
    # the failure mode where a stale dita/ tree silently survives a switch of
    # input CSV. (``--clean`` is now the default and the flag is a deprecated
    # no-op, retained only so existing tuned wrappers keep parsing.)
    if args.out.exists():
        LOGGER.info("Cleaning existing output tree at %s", args.out)
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    try:
        rows = read_csv(args.csv_path)
    except Exception as exc:
        LOGGER.error("Failed to read CSV: %s", exc)
        return 1

    unassigned = check_main_chapter_assigned(rows)
    if unassigned:
        for msg in unassigned:
            LOGGER.error(msg)
        LOGGER.error(
            "Aborting: %d main row(s) have no week assigned. Each week is a "
            "top-level entry in the main ditamap, so every main gram must "
            "land under a week — fill in target_chapter and re-run.",
            len(unassigned),
        )
        return 1

    # A blank Zone-A identity column aborts here (constitution VII): a defect
    # in our own artifact, distinct from the duplicate-identity *warning* below.
    try:
        duplicates = check_row_identity(rows)
    except PipelineDataError as exc:
        LOGGER.error("Aborting: %s", exc)
        return 1
    if duplicates:
        for msg in duplicates:
            LOGGER.warning(msg)
        LOGGER.warning(
            "Continuing despite %d duplicate row identit%s — affected grams "
            "will be merged into one topic with partial content "
            "(later row's analysis section drops, GLC sections interleave). "
            "Run deduplicate_csv.py to renumber before final emission.",
            len(duplicates), "y" if len(duplicates) == 1 else "ies",
        )

    written: list[Path] = []
    skipped: list[dict] = []
    errors = 0
    redirected_total = 0
    # Index pass (feature 006): map each master row's png_path to its output
    # location so redirected rows can link to it. Inert when no row redirects.
    # A blank ``.wav`` view field is hard-failed here (constitution VII).
    try:
        master_index = build_master_index(rows, args.out)
        gram_groups = _gram_groups(rows)
    except PipelineDataError as exc:
        LOGGER.error("Aborting: %s", exc)
        return 1
    for key, gram_rows in gram_groups.items():
        try:
            paths, skips, redirected = emit_gram_topic(
                gram_rows, args.out, args.image_root,
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

    # Common static pages (feature 010): copy the static tree into each
    # publication folder, then reference them as the first ditamap entries.
    static_pages = discover_static_pages(args.static_root)
    if static_pages:
        LOGGER.info("Common static pages (first ditamap entries): %s",
                    ", ".join(static_pages))
    else:
        LOGGER.warning(
            "No static pages found under %s — ditamaps carry only their "
            "content nav (top-level Week folders for main, the Grams folder "
            "for progress tests), no shared Welcome/Security pages.",
            args.static_root)
    static_copied: list[Path] = []
    for pub in publications:
        copied = copy_static_tree(args.static_root, args.out / pub)
        static_copied.extend(copied)
        if copied:
            LOGGER.info("Copied %d static file(s) into %s/", len(copied), pub)

    ditamap_paths: list[Path] = []
    if any(r["publication"] == "main" for r in rows):
        # Week sub-documents: one chapter topic per effective main chapter,
        # referenced (not topichead-ed) by the main ditamap so each week is
        # its own page at the top level of the map.
        chapter_topics = emit_main_chapter_topics(rows, args.out)
        for path in chapter_topics:
            written.append(path)
            LOGGER.info("Wrote %s", path)
        ditamap_paths.append(emit_main_ditamap(rows, args.out, static_pages))
        LOGGER.info("Wrote ditamap %s", ditamap_paths[-1])
    for pub in publications:
        if pub != "main":
            path = emit_test_ditamap(pub, rows, args.out, static_pages)
            ditamap_paths.append(path)
            LOGGER.info("Wrote ditamap %s", path)

    ditaval_path = write_trainee_ditaval(args.out)
    LOGGER.info("Wrote DITAVAL profile %s", ditaval_path)

    manifest_path = write_manifest(
        args.out, written + static_copied + ditamap_paths + [ditaval_path])
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
