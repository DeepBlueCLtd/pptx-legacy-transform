"""Prep-time transform: relink ``.wav``-backed GLCs to author-supplied images.

The author is migrating legacy "live-render" grams -- where a ``.glc`` config
points at a ``.wav`` that the on-PC GLC viewer renders -- to pre-rendered
spectrogram images. For each such gram the author exports a replacement image
and copies it into the same folder as the existing ``.glc``/``.wav`` pair. This
script walks a content tree and, for every ``.glc`` whose inner asset is still a
``.wav``, finds the matching image and rewrites the ``.glc``'s
``<data_source><filename>`` to point at the image instead.

That single edit is the whole conversion: ``generate_dita.py`` dispatches purely
on the GLC's inner asset extension -- ``.wav`` is surfaced as a link, ``.png`` /
``.jpg`` is embedded inline -- so flipping the filename turns a live-render gram
into an embedded-image gram. No CSV edit is involved.

Matching (per folder). A *conversion-candidate image* is a file whose basename
matches ``Image <N>-...`` with an image extension; the ``Image <N>`` prefix flags
it as an author-supplied replacement (so pre-existing topic images like
``lofar-1-i.png`` are ignored) and yields the image number for Pattern B. For
each ``.wav``-backed ``.glc`` the wav's own name selects the rule:

* Pattern B -- if the wav is named ``WAV <n>``, match the candidate image whose
  number equals ``n`` (e.g. ``WAV 1.wav`` -> ``Image 1-0-110 Hz.jpg``).
* Pattern A -- otherwise match the candidate image whose stem *ends with* the wav
  stem (e.g. ``45 - 99 Hz.wav`` -> ``Image 1-45 - 99 Hz.jpg``).

On a unique match the ``.glc`` is rewritten (a targeted text replace of the
``<filename>`` text, leaving the rest of the file byte-for-byte intact) and the
referenced ``.wav`` is moved aside to ``<name>.wav.bak``. Zero or 2+ matches log
a warning and leave the pair untouched. A ``.glc`` already pointing at an image
is skipped, so the transform is idempotent and re-runnable: once converted, a
gram is never reconsidered.

Logging follows the dual-output convention: stdout + ``relink.log`` in the cwd.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Sequence

# Sibling-import the canonical GLC parser (mirrors introspect_pptx.py) so this
# script reads a .glc exactly as the rest of the pipeline does.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_to_csv import parse_glc  # noqa: E402

LOGGER = logging.getLogger(__name__)

# Image extensions a relinked GLC may point at (mirrors the generator's inline
# dispatch set, minus .wav).
IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif")

# An author-supplied replacement image is named "Image <N>-..." (one-based,
# whitespace tolerated). The captured number drives Pattern B.
IMAGE_PREFIX_RE = re.compile(r"^Image\s*(\d+)\b", re.IGNORECASE)

# A numbered wav is named "WAV <n>" with nothing else (Pattern B). The captured
# number is matched against the image number.
NUMBERED_WAV_RE = re.compile(r"^WAV\s*(\d+)$", re.IGNORECASE)

# Targeted rewrite of the first <filename>...</filename> inner text. Non-greedy
# so it stops at the first close tag; the rest of the file is left untouched.
FILENAME_TAG_RE = re.compile(r"(<filename>)(.*?)(</filename>)", re.DOTALL)


# -----------------------------------------------------------------------------
# Logging convention -- mirrored across the stage scripts.
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
# Discovery and matching
# -----------------------------------------------------------------------------

@dataclass
class CandidateImage:
    number: int
    path: Path


@dataclass
class MatchResult:
    image: Optional[Path] = None
    reason: str = ""  # populated only when image is None


def iter_glc_files(root: Path) -> Iterator[Path]:
    """Yield every ``.glc`` under ``root`` in deterministic (sorted) order."""
    for path in sorted(root.rglob("*.glc")):
        if path.is_file():
            yield path


def candidate_images(folder: Path) -> list[CandidateImage]:
    """Return the ``Image <N>-...`` replacement images in ``folder``, sorted."""
    out: list[CandidateImage] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        m = IMAGE_PREFIX_RE.match(path.name)
        if not m:
            continue
        out.append(CandidateImage(number=int(m.group(1)), path=path))
    return out


def _normalise(text: str) -> str:
    """Lower-case and collapse internal whitespace for tolerant comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def match_image(wav_filename: str, candidates: Sequence[CandidateImage]) -> MatchResult:
    """Match a wav (by its filename) to exactly one candidate image.

    The wav's name selects the rule: ``WAV <n>`` -> number match (Pattern B);
    anything else -> stem-suffix match (Pattern A). Returns the single matching
    image, or a ``reason`` explaining a zero / ambiguous outcome.
    """
    wav_stem = Path(wav_filename).stem

    numbered = NUMBERED_WAV_RE.match(wav_stem)
    if numbered:
        wav_number = int(numbered.group(1))
        hits = [c for c in candidates if c.number == wav_number]
        kind = "number %d" % wav_number
    else:
        wav_norm = _normalise(wav_stem)
        hits = [c for c in candidates if _normalise(c.path.stem).endswith(wav_norm)]
        kind = "suffix %r" % wav_stem

    if not hits:
        return MatchResult(reason="no candidate image matches %s" % kind)
    if len(hits) > 1:
        names = ", ".join(sorted(c.path.name for c in hits))
        return MatchResult(reason="ambiguous, %d images match %s: %s"
                           % (len(hits), kind, names))
    return MatchResult(image=hits[0].path)


# -----------------------------------------------------------------------------
# Mutation
# -----------------------------------------------------------------------------

def rewrite_glc_filename(glc_path: Path, new_basename: str) -> None:
    """Replace the first ``<filename>`` inner text with ``new_basename``.

    A targeted text replace -- not an XML round-trip -- so every other byte of
    the file is preserved (determinism / minimal churn). Reads and writes UTF-8.
    """
    text = glc_path.read_text(encoding="utf-8")
    new_text, count = FILENAME_TAG_RE.subn(
        lambda m: m.group(1) + new_basename + m.group(3), text, count=1)
    if count != 1:
        # parse_glc already confirmed a <filename>; this guards a malformed file.
        raise ValueError("no <filename> element to rewrite in %s" % glc_path)
    glc_path.write_text(new_text, encoding="utf-8")


def move_wav_aside(wav_path: Path) -> bool:
    """Rename ``foo.wav`` -> ``foo.wav.bak`` so it can't re-trigger a match.

    Returns True if a file was moved; False (with a warning) if the ``.wav`` is
    absent -- a missing source asset dangles, it doesn't crash the run.
    """
    if not wav_path.is_file():
        LOGGER.warning("referenced wav not on disk, nothing to move aside: %s", wav_path)
        return False
    backup = wav_path.with_name(wav_path.name + ".bak")
    wav_path.replace(backup)
    LOGGER.debug("moved %s -> %s", wav_path.name, backup.name)
    return True


# -----------------------------------------------------------------------------
# Per-folder processing and summary
# -----------------------------------------------------------------------------

@dataclass
class Tally:
    relinked: int = 0
    skipped_no_match: int = 0
    skipped_ambiguous: int = 0
    already_image: int = 0
    skipped_unreadable: int = 0


def process_glc(glc_path: Path, candidates: Sequence[CandidateImage], *,
                dry_run: bool, tally: Tally) -> None:
    """Inspect one ``.glc`` and, if it points at a matchable wav, relink it."""
    doc = parse_glc(glc_path)
    inner = doc.image_filename
    if not inner:
        LOGGER.warning("skip (no inner filename): %s [%s]",
                       glc_path, "; ".join(doc.warnings) or "unknown")
        tally.skipped_unreadable += 1
        return

    if Path(inner).suffix.lower() != ".wav":
        # Already an image (or some other non-wav target): nothing to do.
        LOGGER.debug("skip (already points at %s): %s", inner, glc_path)
        tally.already_image += 1
        return

    result = match_image(inner, candidates)
    if result.image is None:
        LOGGER.warning("skip (%s): %s -> %s", result.reason, glc_path.name, inner)
        if result.reason.startswith("ambiguous"):
            tally.skipped_ambiguous += 1
        else:
            tally.skipped_no_match += 1
        return

    image_name = result.image.name
    if dry_run:
        LOGGER.info("[dry-run] would relink %s: %s -> %s",
                    glc_path, inner, image_name)
        tally.relinked += 1
        return

    rewrite_glc_filename(glc_path, image_name)
    move_wav_aside(glc_path.with_name(inner))
    LOGGER.info("relinked %s: %s -> %s", glc_path, inner, image_name)
    tally.relinked += 1


def relink_tree(root: Path, *, dry_run: bool) -> Tally:
    """Walk ``root`` and relink every wav-backed ``.glc`` it can match."""
    tally = Tally()
    # Cache per-folder candidate lists so a folder is scanned once even when it
    # holds several .glc files.
    cache: dict[Path, list[CandidateImage]] = {}
    for glc_path in iter_glc_files(root):
        folder = glc_path.parent
        if folder not in cache:
            cache[folder] = candidate_images(folder)
        process_glc(glc_path, cache[folder], dry_run=dry_run, tally=tally)
    return tally


def _emit_summary(tally: Tally, *, dry_run: bool) -> None:
    verb = "would relink" if dry_run else "relinked"
    LOGGER.info(
        "done: %s %d, skipped %d (no match), %d (ambiguous), %d (already image), "
        "%d (unreadable)",
        verb, tally.relinked, tally.skipped_no_match, tally.skipped_ambiguous,
        tally.already_image, tally.skipped_unreadable)


def main(argv: list[str] | None = None) -> int:
    setup_logging(Path("relink.log"))
    parser = argparse.ArgumentParser(
        description="Relink .wav-backed GLCs to author-supplied images (prep-time).")
    parser.add_argument("--root", required=True, type=Path, dest="root",
                        help="content tree to walk for .glc files")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="report proposed relinks without modifying anything")
    args = parser.parse_args(argv)

    root: Path = args.root
    if not root.exists():
        LOGGER.error("root does not exist: %s", root)
        return 1
    if not root.is_dir():
        LOGGER.error("root is not a directory: %s", root)
        return 1

    LOGGER.info("relinking wav-backed GLCs under %s%s",
                root, " (dry-run)" if args.dry_run else "")
    tally = relink_tree(root, dry_run=args.dry_run)
    _emit_summary(tally, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":  # pragma: no cover
    rc = main()
    # Preserve CLI exit codes when invoked as a script, but stay silent when
    # invoked from an interactive REPL via runpy.run_path -- sys.exit would
    # otherwise kill the interpreter. sys.ps1 is only defined interactively.
    if rc and not hasattr(sys, "ps1"):
        sys.exit(rc)
