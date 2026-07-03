"""Snapshotter (Feature 007): render Word analysis sheets to sibling PNGs.

Prep-time, render-once stage of the migration pipeline. Walks a content
tree, selects every Word *analysis* sheet (``*analysis*`` + ``.doc``/
``.docx``) and renders each to a same-stem ``.png`` sibling so the
downstream pipeline embeds the analysis table **inline** instead of
leaving a click-to-open link that launches MS Word mid-lesson.

The mechanism is an external, configurable renderer (LibreOffice headless
``soffice`` by default), invoked once per un-rendered sheet via
``subprocess`` -- exactly as feature 001 contains DITA-OT. The script's
runtime-critical path is **stdlib only** (the reverse ``.docx`` wrap uses
``zipfile`` + ``xml.etree``); the only optional library is Pillow, imported
defensively inside :func:`tidy_image` with a full-page fallback when absent.

Design invariants (see specs/007-analysis-sheet-images/):

- **Render-once / idempotent.** A sheet that already has its sibling ``.png``
  is skipped; the rendered PNG is a committed source asset, so the renderer
  never runs inside the re-runnable generate/publish loop (research R2).
- **Warn-and-defer.** A renderer failure, an unavailable renderer, a
  multi-page source, an absent image library, or a wrap failure is a WARNING
  that defers -- the run continues and exits 0; never an abort, never a
  silent truncation (Principle IV, research R3/R5).
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
    docx_wrapped: bool = False
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
# Reverse wrap: guarantee a .docx form too (Phase 6: FR-018, research R9).
# -----------------------------------------------------------------------------

_DOCX_FIXED_DATE = (1980, 1, 1, 0, 0, 0)

_WRAP_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_WRAP_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_WRAP_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>"""

# A full-page inline image. The EMU extents are nominal (a landscape page at
# 96 DPI); Word/consumers scale to the embedded PNG. The point is a valid,
# parseable .docx that embeds the rendered analysis image (research R9).
_WRAP_DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
<w:body>
<w:p><w:r><w:drawing>
<wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="9144000" cy="6858000"/>
<wp:docPr id="1" name="AnalysisSheet"/>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic>
<pic:nvPicPr><pic:cNvPr id="1" name="AnalysisSheet"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="9144000" cy="6858000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic>
</a:graphicData></a:graphic>
</wp:inline>
</w:drawing></w:r></w:p>
</w:body>
</w:document>"""


def wrap_png_in_docx(png: Path, docx_out: Path) -> bool:
    """Emit a minimal full-page ``.docx`` embedding ``png``.

    Reuses the stdlib ``zipfile`` + fixed-timestamp pattern from
    ``mock_pptx.emit_docx`` so the output is byte-stable and idempotent
    (Principle V, research R9). Returns ``False`` on a filesystem error.
    **Never raises.**
    """
    try:
        image_bytes = png.read_bytes()
    except OSError as exc:
        LOGGER.warning("reverse wrap failed (cannot read %s): %s", png, exc)
        return False
    try:
        docx_out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(docx_out, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in (
                ("[Content_Types].xml", _WRAP_CONTENT_TYPES),
                ("_rels/.rels", _WRAP_ROOT_RELS),
                ("word/_rels/document.xml.rels", _WRAP_DOC_RELS),
                ("word/document.xml", _WRAP_DOCUMENT),
            ):
                info = zipfile.ZipInfo(filename=name, date_time=_DOCX_FIXED_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, content)
            img_info = zipfile.ZipInfo(
                filename="word/media/image1.png", date_time=_DOCX_FIXED_DATE)
            img_info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(img_info, image_bytes)
        return True
    except OSError as exc:
        LOGGER.warning("reverse wrap failed (%s): %s", docx_out, exc)
        return False


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


def _reverse_wrap_png_only(
    content_root: Path, dry_run: bool, extra_names: tuple[str, ...] = (),
) -> list[SnapshotResult]:
    """For every analysis ``.png`` with no same-stem ``.docx``, emit one.

    Selection mirrors :func:`iter_analysis_sheets` (``*analysis*`` plus the
    ``extra_names`` tokens) so an opted-in sheet rides the same FR-018 path.
    """
    results: list[SnapshotResult] = []
    for png in sorted(content_root.rglob("*")):
        if not png.is_file() or png.suffix.lower() != ".png":
            continue
        if not _is_analysis_name(png.stem, extra_names):
            continue
        docx_out = png.with_suffix(".docx")
        if docx_out.exists():
            continue
        if dry_run:
            LOGGER.info("would wrap PNG into .docx: %s -> %s", png, docx_out)
            results.append(SnapshotResult(
                source_path=png, outcome="skipped_has_png", docx_wrapped=True))
            continue
        if wrap_png_in_docx(png, docx_out):
            LOGGER.info("wrapped PNG into .docx: %s -> %s", png, docx_out)
            results.append(SnapshotResult(
                source_path=png, outcome="skipped_has_png", docx_wrapped=True))
    return results


def _emit_summary(results: list[SnapshotResult]) -> None:
    """Log + print the end-of-run summary (FR-014)."""
    sheets_seen = sum(1 for r in results if r.source_path.suffix.lower() in WORD_SUFFIXES)
    rendered = sum(1 for r in results if r.outcome == "rendered")
    skipped = sum(1 for r in results
                  if r.outcome == "skipped_has_png"
                  and r.source_path.suffix.lower() in WORD_SUFFIXES)
    render_failed = sum(1 for r in results if r.outcome == "render_failed")
    multipage_warned = sum(1 for r in results if r.multipage)
    docx_wrapped = sum(1 for r in results if r.docx_wrapped)
    tidy_skipped = sum(1 for r in results if r.outcome == "rendered" and not r.tidied)
    summary = (
        "snapshot summary: "
        f"sheets_seen={sheets_seen} rendered={rendered} "
        f"skipped_has_png={skipped} render_failed={render_failed} "
        f"multipage_warned={multipage_warned} docx_wrapped={docx_wrapped} "
        f"tidy_skipped={tidy_skipped}"
    )
    LOGGER.info("%s", summary)
    print(summary)


def snapshot(
    content_root: Path, renderer_cmd: str, dry_run: bool,
    reverse_wrap: bool = True, extra_names: Iterable[str] = (),
) -> list[SnapshotResult]:
    """Scan ``content_root``, render/skip each analysis sheet, reverse-wrap.

    ``reverse_wrap`` controls FR-018 (synthesise a ``.docx`` wrapper around
    any ``*analysis*.png`` that has no same-stem ``.docx`` so editors get a
    Word source). Default ``True`` preserves the original feature 007
    contract; pass ``False`` (CLI ``--no-reverse-wrap``) when the corpus
    is read-only-by-policy and synthesised ``.docx`` files would be noise.

    ``extra_names`` (CLI ``--extra-name``, repeatable) opts in analysis
    sheets whose filenames lack the ``analysis`` token; each entry is a
    case-insensitive substring matched against the stem. Blank tokens are
    dropped with a WARNING.
    """
    tokens = _normalise_extra_names(extra_names)
    results: list[SnapshotResult] = []
    for doc in iter_analysis_sheets(content_root, tokens):
        results.append(_process_sheet(doc, renderer_cmd, dry_run))
    if reverse_wrap:
        results.extend(_reverse_wrap_png_only(content_root, dry_run, tokens))
    return results


def main(argv: list[str] | None = None) -> int:
    setup_logging(Path("snapshot.log"))
    parser = argparse.ArgumentParser(
        description="Render Word analysis sheets to sibling PNGs (prep-time).")
    parser.add_argument("--content-root", required=True, type=Path, dest="content_root")
    parser.add_argument("--renderer-cmd", default="soffice", dest="renderer_cmd")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument(
        "--no-reverse-wrap", action="store_false", dest="reverse_wrap",
        help="Skip FR-018's reverse-wrap step (synthesising a .docx around "
             "every PNG-only analysis sheet). Use when the source corpus "
             "should not be mutated with new .docx files — only render "
             ".doc/.docx -> .png siblings.")
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

    LOGGER.info(
        "snapshotting analysis sheets under %s (renderer=%r%s%s%s)",
        content_root, args.renderer_cmd,
        ", dry-run" if args.dry_run else "",
        "" if args.reverse_wrap else ", no-reverse-wrap",
        ", extra-names=%r" % (args.extra_names,) if args.extra_names else "")
    try:
        results = snapshot(
            content_root, args.renderer_cmd, args.dry_run,
            reverse_wrap=args.reverse_wrap,
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
