"""Snapshotter (Feature 007): render Word analysis sheets to sibling PNGs.

Prep-time, render-once stage of the migration pipeline. Walks a content
tree, selects every Word *analysis* sheet (``*analysis*`` + ``.doc``/
``.docx``) and renders each to a same-stem ``.png`` sibling so the
downstream pipeline embeds the analysis table **inline** instead of
leaving a click-to-open link that launches MS Word mid-lesson.

The mechanism is an external, configurable renderer (LibreOffice headless
``soffice`` by default), invoked once per un-rendered sheet via
``subprocess`` -- exactly as feature 001 contains DITA-OT. The script's
runtime-critical path is **stdlib only**; the only optional library is Pillow,
imported defensively inside :func:`tidy_image` with a full-page fallback when
absent.

The conversion runs in **one direction only**: Word document -> PNG. Feature 013
supersedes feature 007's FR-018, which used to synthesise a ``.docx`` around any
analysis PNG lacking one -- so the pipeline no longer creates Word documents,
and every Word document in a source tree is one an author wrote. ``--sweep-
wrappers`` retracts the fabricated files earlier runs left behind.

Design invariants (see specs/007-analysis-sheet-images/ and
specs/013-analysis-word-originals/):

- **Render-once / idempotent.** A sheet that already has its sibling ``.png``
  is skipped; the rendered PNG is a committed source asset, so the renderer
  never runs inside the re-runnable generate/publish loop (research R2).
- **Warn-and-defer.** A renderer failure, an unavailable renderer, a
  multi-page source, or an absent image library is a WARNING that defers --
  the run continues and exits 0; never an abort, never a silent truncation
  (Principle IV, research R3/R5).
- **The sweep never guesses.** Deletion is opt-in (``--apply``) and keys on a
  full content signature, so its failure mode is leaving a file alone rather
  than destroying an author's document.
- **Selection keys on the name, not "every Word doc".** Analysis sheets share
  the chapter folder with PPT source data and unrelated Word documents, so
  selection matches the ``*analysis*`` naming convention (research R7).
  Corpus sheets that deviate from the convention (e.g. ``V III .doc``) are
  opted in per-run with repeatable ``--extra-name`` tokens; the token list is
  per-corpus configuration, so it belongs in the parent wrapper/orchestrator
  script that invokes this one, never hard-coded here.

Logging follows the project convention: dual stdout + ``snapshot.log``,
DEBUG to file, INFO/WARNING to console.
"""

from __future__ import annotations

import argparse
import logging
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


LOGGER = logging.getLogger(__name__)

# Files matching this name substring (case-insensitive) with a Word
# extension are analysis sheets. Selection keys on the corpus naming
# convention so unrelated ``source_data.doc`` siblings are left untouched.
ANALYSIS_NAME_TOKEN = "analysis"
# Known misspellings of the analysis token seen in legacy decks (e.g.
# ``analaysis.doc``). Matched alongside the correct token so a typo'd sheet
# still renders and flows through the pipeline instead of being silently
# skipped. This is a general typo-tolerance for the one selection token, not
# a corpus-specific opt-in (those stay in ``--extra-name`` per the wrapper).
# generate_dita.py corrects the same misspellings when it names the emitted
# asset, so the published href reads ``analysis`` regardless.
ANALYSIS_NAME_MISSPELLINGS = ("analaysis",)
WORD_SUFFIXES = (".doc", ".docx")


# -----------------------------------------------------------------------------
# Logging convention -- mirrors extract_to_csv.py / generate_dita.py.
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
# Per-sheet result (transient; drives logging + the end-of-run summary).
# -----------------------------------------------------------------------------

@dataclass
class SnapshotResult:
    """One record per analysis document visited. Not persisted."""

    source_path: Path
    outcome: str  # "rendered" | "skipped_has_png" | "render_failed"
    multipage: bool = False
    tidied: bool = False
    warning: str | None = None


# -----------------------------------------------------------------------------
# Selection + classification (Phase 2: FR-015, research R7).
# -----------------------------------------------------------------------------

def _normalise_extra_names(extra_names: Iterable[str]) -> tuple[str, ...]:
    """Strip, lower-case, and de-blank the operator-supplied extra tokens.

    Blank tokens are dropped with a WARNING: an empty substring would match
    every Word document, silently defeating the FR-015 selection guard.
    """
    kept: list[str] = []
    for token in extra_names:
        cleaned = token.strip().lower()
        if cleaned:
            kept.append(cleaned)
        else:
            LOGGER.warning("ignoring blank --extra-name token")
    return tuple(kept)


def _is_analysis_name(stem: str, extra_names: tuple[str, ...] = ()) -> bool:
    """True iff ``stem`` names an analysis sheet.

    Matches the ``*analysis*`` convention (case-insensitive), a known
    misspelling of that token (``ANALYSIS_NAME_MISSPELLINGS``, e.g.
    ``analaysis``), or any of the ``extra_names`` tokens, each matched the
    same way -- as a case-insensitive substring of the stem (research R7:
    deviating corpus sheets are opted in by name, the hyperlink-driven
    alternative stays rejected).
    """
    lowered = stem.lower()
    if ANALYSIS_NAME_TOKEN in lowered:
        return True
    if any(typo in lowered for typo in ANALYSIS_NAME_MISSPELLINGS):
        return True
    return any(token.lower() in lowered for token in extra_names if token)


def iter_analysis_sheets(
    content_root: Path, extra_names: tuple[str, ...] = (),
) -> Iterator[Path]:
    """Yield every Word analysis sheet under ``content_root``.

    A file qualifies when its **name contains ``analysis``** (case-insensitive)
    AND its suffix is ``.doc``/``.docx``. Unrelated Word documents sharing the
    chapter folder (e.g. ``source_data.doc``) are NOT yielded. ``extra_names``
    opts in sheets whose names deviate from the convention (e.g. ``X-aaa.doc``):
    each token is matched exactly like the built-in ``analysis`` token.
    Iteration is deterministic (sorted) for byte-stable logs and idempotent
    re-runs.
    """
    for path in sorted(content_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in WORD_SUFFIXES:
            continue
        if not _is_analysis_name(path.stem, extra_names):
            continue
        yield path


def needs_render(doc: Path) -> bool:
    """True iff no same-stem ``.png`` sibling exists for ``doc``."""
    return not doc.with_suffix(".png").exists()


# -----------------------------------------------------------------------------
# Rendering (Phase 3/4: FR-007, FR-008, FR-016).
# -----------------------------------------------------------------------------

def _renderer_argv(renderer_cmd: str) -> list[str]:
    """Split a (possibly multi-token) renderer command into argv.

    The default ``soffice`` is a single token; a test stub or a quoted path
    with spaces is handled by ``shlex``. Operators on Windows should quote
    paths containing spaces (documented in the README).
    """
    return shlex.split(renderer_cmd) or [renderer_cmd]


def _run_renderer(renderer_cmd: str, convert_to: str, outdir: Path, doc: Path):
    """Invoke the renderer for one ``--convert-to`` target. Returns the
    ``CompletedProcess`` or raises ``FileNotFoundError`` when the renderer
    binary is absent (handled by the callers)."""
    argv = _renderer_argv(renderer_cmd) + [
        "--headless", "--convert-to", convert_to,
        "--outdir", str(outdir), str(doc),
    ]
    LOGGER.debug("renderer invocation: %s", argv)
    return subprocess.run(argv, capture_output=True, text=True)


def render_doc_to_png(doc: Path, png_out: Path, renderer_cmd: str) -> bool:
    """Render ``doc``'s first page to ``png_out`` (a same-stem sibling).

    Shells out to ``<renderer> --headless --convert-to png --outdir <tmp>
    <doc>`` then moves the produced PNG into place. Returns ``True`` on
    success. Logs a WARNING and returns ``False`` on a non-zero exit or an
    unavailable renderer. **Never raises.**
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            result = _run_renderer(renderer_cmd, "png", tmp_dir, doc)
        except FileNotFoundError:
            LOGGER.warning(
                "render failed (renderer %r not found): %s", renderer_cmd, doc)
            return False
        except OSError as exc:
            LOGGER.warning("render failed (%s): %s", exc, doc)
            return False
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            first = detail[0] if detail else f"exit {result.returncode}"
            LOGGER.warning("render failed (%s): %s", first, doc)
            return False
        produced = tmp_dir / (doc.stem + ".png")
        if not produced.exists():
            # Some renderers name the output after the source stem; if the
            # exact name is absent, fall back to the sole PNG in the tmp dir.
            pngs = sorted(tmp_dir.glob("*.png"))
            if not pngs:
                LOGGER.warning("render produced no PNG: %s", doc)
                return False
            produced = pngs[0]
        png_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), str(png_out))
        return True


# -----------------------------------------------------------------------------
# Multi-page detection (Phase 4: FR-016, research R3).
# -----------------------------------------------------------------------------

_PDF_PAGES_COUNT = re.compile(
    rb"/Type\s*/Pages\b.{0,800}?/Count\s+(\d+)", re.DOTALL)
_PDF_COUNT_PAGES = re.compile(
    rb"/Count\s+(\d+)\b.{0,800}?/Type\s*/Pages", re.DOTALL)
_PDF_ANY_COUNT = re.compile(rb"/Count\s+(\d+)")


def _page_count_from_pdf_bytes(data: bytes) -> int | None:
    """Tolerantly read the page-tree ``/Count`` from PDF bytes.

    LibreOffice writes ``/Type /Pages /Count N`` in cleartext. Returns the
    integer page count, or ``None`` when it cannot be determined.
    """
    for pattern in (_PDF_PAGES_COUNT, _PDF_COUNT_PAGES, _PDF_ANY_COUNT):
        match = pattern.search(data)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def page_count(doc: Path, renderer_cmd: str) -> int | None:
    """Return ``doc``'s page count via a companion ``--convert-to pdf``.

    Returns ``None`` when the count cannot be determined (renderer absent,
    non-zero exit, or an unreadable PDF). **Never raises.**
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            result = _run_renderer(renderer_cmd, "pdf", tmp_dir, doc)
        except OSError:
            return None
        if result.returncode != 0:
            return None
        pdfs = sorted(tmp_dir.glob("*.pdf"))
        if not pdfs:
            return None
        try:
            data = pdfs[0].read_bytes()
        except OSError:
            return None
    return _page_count_from_pdf_bytes(data)


# -----------------------------------------------------------------------------
# Tidy: margin-trim + DPI (Phase 5: FR-017, research R8).
# -----------------------------------------------------------------------------

TIDY_MARGIN_PX = 8
TIDY_DPI = (150, 150)


def tidy_image(png: Path) -> bool:
    """Trim page-margin whitespace and normalise DPI on ``png`` in place.

    Uses Pillow, imported **defensively** inside the function. When Pillow is
    absent (or any processing error occurs) the full-page render is left
    untouched, an INFO/WARNING line is logged, and ``False`` is returned.
    **Never raises.** (FR-017 graceful degradation.)
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        LOGGER.info(
            "Pillow not installed; keeping full-page render (tidy skipped): %s",
            png)
        return False
    try:
        with Image.open(png) as im:
            rgb = im.convert("RGB")
            background = Image.new("RGB", rgb.size, (255, 255, 255))
            diff = ImageChops.difference(rgb, background)
            bbox = diff.getbbox()
            if bbox is None:
                # Entirely white -- nothing to crop; still normalise DPI.
                cropped = im.copy()
            else:
                left = max(bbox[0] - TIDY_MARGIN_PX, 0)
                top = max(bbox[1] - TIDY_MARGIN_PX, 0)
                right = min(bbox[2] + TIDY_MARGIN_PX, im.width)
                bottom = min(bbox[3] + TIDY_MARGIN_PX, im.height)
                cropped = im.crop((left, top, right, bottom))
            cropped.save(png, dpi=TIDY_DPI)
        return True
    except Exception as exc:  # noqa: BLE001 -- never let tidy break the run
        LOGGER.warning("tidy failed (%s); keeping full-page render: %s", exc, png)
        return False


# -----------------------------------------------------------------------------
# Wrapper sweep (Feature 013): retract the .docx files feature 007 fabricated.
# -----------------------------------------------------------------------------
#
# Feature 007's FR-018 guaranteed every analysis sheet existed in both an image
# and a Word form, synthesising a minimal ``.docx`` around any analysis PNG that
# had no Word sibling. That guarantee is **superseded** (see
# specs/013-analysis-word-originals/): the wrapper was created precisely where
# no editable original had ever existed, and its entire content was the same
# picture the gram page already showed. Feature 013 carries genuine Word
# originals into the DITA tree, which makes "is there a Word document in this
# folder?" the signal an analyst reads as "there is a source I can amend" -- and
# a wrapper makes that signal always true and therefore worthless.
#
# The synthesis step is gone. These functions retract what earlier runs already
# wrote into source trees, because removing the step does not delete its output.
#
# Detection is by **content signature**, never filename, timestamp, or size: a
# fabricated wrapper is a zip whose part list is exactly the five parts the
# generator wrote, whose document body carries the generator's ``AnalysisSheet``
# drawing name, and which embeds exactly one PNG. A genuine Word document --
# even one whose only visible content is a full-page image an author pasted in
# -- carries styles, settings, fontTable, and docProps parts that the fabricated
# one never had, so it cannot collide with this signature.

# The exact part list the removed wrapper generator emitted, in any order.
_WRAPPER_PARTS = frozenset({
    "[Content_Types].xml",
    "_rels/.rels",
    "word/_rels/document.xml.rels",
    "word/document.xml",
    "word/media/image1.png",
})

# The drawing name the removed generator gave its full-page image. Present in
# both the ``wp:docPr`` and ``pic:cNvPr`` elements it wrote.
_WRAPPER_MARKER = b"AnalysisSheet"


def is_fabricated_wrapper(path: Path) -> bool:
    """True iff ``path`` is a ``.docx`` fabricated by the removed wrap step.

    Requires **every** signature element to match (FR-014). Anything unreadable,
    not a zip, or structurally different is reported as *not* a wrapper: the
    sweep's failure mode must be leaving a file alone, never deleting an
    author's document. Never raises.
    """
    if path.suffix.lower() != ".docx":
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            if frozenset(zf.namelist()) != _WRAPPER_PARTS:
                return False
            return _WRAPPER_MARKER in zf.read("word/document.xml")
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        LOGGER.debug("not a readable .docx, leaving alone (%s): %s", exc, path)
        return False


def find_fabricated_wrappers(content_root: Path) -> list[Path]:
    """Return every fabricated wrapper under ``content_root``, sorted.

    Scans all ``.docx`` files, not just those beside a PNG. The removed step's
    existence check looked only for a same-stem ``.docx`` and never a ``.doc``,
    so in the legacy ``.doc`` decks it fabricated a wrapper *next to a genuine
    ``analysis.doc``* (FR-015); a scan that skipped folders already holding a
    Word document would miss exactly those. Sorted for deterministic reporting.
    """
    return sorted(
        p for p in content_root.rglob("*.docx")
        if p.is_file() and is_fabricated_wrapper(p)
    )


def sweep_wrappers(content_root: Path, apply_changes: bool = False) -> list[Path]:
    """Report (and with ``apply_changes``, delete) fabricated wrappers.

    Returns the wrappers found, whether or not they were deleted. Reporting is
    the default and deleting is the opt-in (FR-016), following the verify-then-
    apply convention ``ingest_gram_images.py`` already establishes for the
    destructive prep stages -- this is the only step in feature 013 that removes
    files, so the operator sees the list before anything happens to it.

    Idempotent (013 FR-018): a swept tree yields an empty list and no filesystem
    change. A file that cannot be deleted is a WARNING that defers, per the
    stage's warn-and-defer invariant.
    """
    found = find_fabricated_wrappers(content_root)
    for wrapper in found:
        if not apply_changes:
            LOGGER.info("would delete fabricated wrapper: %s", wrapper)
            continue
        try:
            wrapper.unlink()
            LOGGER.info("deleted fabricated wrapper: %s", wrapper)
        except OSError as exc:
            LOGGER.warning("could not delete %s: %s", wrapper, exc)
    return found


def _emit_sweep_summary(found: list[Path], apply_changes: bool) -> None:
    """Log + print the sweep's end-of-run summary."""
    if apply_changes:
        summary = f"sweep summary: fabricated_wrappers_found={len(found)} deleted={len(found)}"
    else:
        summary = (
            f"sweep summary: fabricated_wrappers_found={len(found)} deleted=0 "
            "(report-only; re-run with --apply to delete)"
        )
    LOGGER.info("%s", summary)
    print(summary)


# -----------------------------------------------------------------------------
# Main scan loop (FR-001..FR-014).
# -----------------------------------------------------------------------------

def _process_sheet(
    doc: Path, renderer_cmd: str, dry_run: bool) -> SnapshotResult:
    """Classify and (unless --dry-run) render/tidy one analysis sheet."""
    png_out = doc.with_suffix(".png")
    if not needs_render(doc):
        LOGGER.info("skipped (PNG already present): %s", doc)
        return SnapshotResult(source_path=doc, outcome="skipped_has_png")

    if dry_run:
        LOGGER.info("would render: %s -> %s", doc, png_out)
        return SnapshotResult(source_path=doc, outcome="rendered")

    ok = render_doc_to_png(doc, png_out, renderer_cmd)
    if not ok:
        return SnapshotResult(
            source_path=doc, outcome="render_failed",
            warning="analysis image not rendered")

    LOGGER.info("rendered: %s -> %s", doc, png_out)
    result = SnapshotResult(source_path=doc, outcome="rendered")

    # Multi-page detection: keep the page-1 PNG, warn (never truncate silently).
    pages = page_count(doc, renderer_cmd)
    if pages is not None and pages > 1:
        result.multipage = True
        result.warning = f"multi-page source ({pages} pages); only page 1 rendered"
        LOGGER.warning("%s: %s", result.warning, doc)
    elif pages is None:
        LOGGER.warning("page count undetermined (rendered page 1): %s", doc)

    # Tidy the freshly-rendered PNG (graceful fallback when Pillow is absent).
    result.tidied = tidy_image(png_out)
    return result


def _emit_summary(results: list[SnapshotResult]) -> None:
    """Log + print the end-of-run summary (FR-014)."""
    sheets_seen = sum(1 for r in results if r.source_path.suffix.lower() in WORD_SUFFIXES)
    rendered = sum(1 for r in results if r.outcome == "rendered")
    skipped = sum(1 for r in results
                  if r.outcome == "skipped_has_png"
                  and r.source_path.suffix.lower() in WORD_SUFFIXES)
    render_failed = sum(1 for r in results if r.outcome == "render_failed")
    multipage_warned = sum(1 for r in results if r.multipage)
    tidy_skipped = sum(1 for r in results if r.outcome == "rendered" and not r.tidied)
    summary = (
        "snapshot summary: "
        f"sheets_seen={sheets_seen} rendered={rendered} "
        f"skipped_has_png={skipped} render_failed={render_failed} "
        f"multipage_warned={multipage_warned} "
        f"tidy_skipped={tidy_skipped}"
    )
    LOGGER.info("%s", summary)
    print(summary)


def snapshot(
    content_root: Path, renderer_cmd: str, dry_run: bool,
    extra_names: Iterable[str] = (),
) -> list[SnapshotResult]:
    """Scan ``content_root`` and render each un-rendered analysis sheet.

    One direction only: Word document -> sibling PNG. The pipeline no longer
    creates Word documents at all (feature 013 supersedes feature 007's FR-018),
    so every ``.doc``/``.docx`` in a source tree is one an author wrote.

    ``extra_names`` (CLI ``--extra-name``, repeatable) opts in analysis
    sheets whose filenames lack the ``analysis`` token; each entry is a
    case-insensitive substring matched against the stem. Blank tokens are
    dropped with a WARNING.
    """
    tokens = _normalise_extra_names(extra_names)
    results: list[SnapshotResult] = []
    for doc in iter_analysis_sheets(content_root, tokens):
        results.append(_process_sheet(doc, renderer_cmd, dry_run))
    return results


def main(argv: list[str] | None = None) -> int:
    setup_logging(Path("snapshot.log"))
    parser = argparse.ArgumentParser(
        description="Render Word analysis sheets to sibling PNGs (prep-time).")
    parser.add_argument("--content-root", required=True, type=Path, dest="content_root")
    parser.add_argument("--renderer-cmd", default="soffice", dest="renderer_cmd")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument(
        "--sweep-wrappers", action="store_true", dest="sweep_wrappers",
        help="Instead of rendering, find the picture-only .docx files that "
             "feature 007's removed reverse-wrap step fabricated in this tree "
             "and report them. Detection is by content signature, so an "
             "author's own Word document is never matched. Reports only "
             "unless --apply is also given.")
    parser.add_argument(
        "--apply", action="store_true", dest="apply_changes",
        help="With --sweep-wrappers, delete the fabricated wrappers found "
             "instead of only reporting them. Has no effect on its own.")
    parser.add_argument(
        "--extra-name", action="append", default=[], dest="extra_names",
        metavar="TOKEN",
        help="Additional analysis-sheet name token, matched exactly like the "
             "built-in 'analysis' token (case-insensitive substring of the "
             "filename stem). Repeatable. Opts in corpus sheets that do not "
             "follow the *analysis* naming convention (e.g. 'V III .doc'); "
             "the token list is per-corpus configuration, so supply it from "
             "the parent wrapper/orchestrator script.")
    args = parser.parse_args(argv)

    content_root: Path = args.content_root
    if not content_root.exists():
        LOGGER.error("content root does not exist: %s", content_root)
        return 1
    if not content_root.is_dir():
        LOGGER.error("content root is not a directory: %s", content_root)
        return 1

    if args.sweep_wrappers:
        LOGGER.info(
            "sweeping fabricated .docx wrappers under %s (%s)",
            content_root,
            "applying" if args.apply_changes else "report-only")
        try:
            found = sweep_wrappers(content_root, apply_changes=args.apply_changes)
        except OSError as exc:
            LOGGER.error("sweep failed: %s", exc)
            return 1
        _emit_sweep_summary(found, args.apply_changes)
        return 0

    if args.apply_changes:
        LOGGER.warning(
            "--apply has no effect without --sweep-wrappers; rendering as usual.")

    LOGGER.info(
        "snapshotting analysis sheets under %s (renderer=%r%s%s)",
        content_root, args.renderer_cmd,
        ", dry-run" if args.dry_run else "",
        ", extra-names=%r" % (args.extra_names,) if args.extra_names else "")
    try:
        results = snapshot(
            content_root, args.renderer_cmd, args.dry_run,
            extra_names=args.extra_names,
        )
    except OSError as exc:
        LOGGER.error("snapshot failed: %s", exc)
        return 1
    _emit_summary(results)
    return 0


if __name__ == "__main__":  # pragma: no cover
    rc = main()
    # Preserve CLI exit codes when invoked as a script, but stay silent
    # when invoked from an interactive REPL via runpy.run_path —
    # ``sys.exit`` would otherwise kill the interpreter and break the
    # up-arrow iteration loop. ``sys.ps1`` is only defined in
    # interactive sessions.
    if rc and not hasattr(sys, "ps1"):
        sys.exit(rc)
