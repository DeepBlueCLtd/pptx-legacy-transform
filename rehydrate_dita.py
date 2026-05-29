"""Reverse large-asset deduplication (feature 006, User Story 2).

Walks a generated DITA tree and restores any *redirected* lofar to a
self-contained, never-deduplicated form, using only information present in
the DITA content (no reference to the original extraction inputs, FR-008).

A redirected lofar is one whose ``<section>`` carries the provenance
element ``<data name="original-asset-path" value="P">`` that
``generate_dita.py`` emits. For each such lofar this script:

1. Resolves the master file from the lofar's ``<image>``/``<xref>`` href
   (relative to the topic folder).
2. Recomputes the local slug from ``basename(P)`` (the same
   ``slugify_asset_name`` rule the generator uses) and copies the master
   link target back into *this* gram's folder under that slug. For an audio
   pair (``P`` is a ``.glc``) the master ``.glc``'s adjacent ``.wav`` — named
   inside the ``.glc``'s ``<data_source><filename>`` — is restored too, so the
   on-PC GLC viewer's adjacency lookup keeps working (FR-009).
3. Rewrites the lofar href to the local copy and removes the ``<data>``
   element.

A lofar without the ``<data>`` element is left untouched, so running the
script twice is a no-op (idempotent). Serialisation matches the generator's
contract (LF, UTF-8 without BOM, deterministic) so a restored topic is
byte-identical to one that was never deduplicated (SC-004).

Logging convention (R10): dual stdout + ``rehydrate.log`` file handlers,
mirroring ``generate_dita.py``.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import generate_dita
from generate_dita import (
    ORIGINAL_ASSET_PATH, _serialise, _write_text, slugify_asset_name,
)

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


def _basename(path: str) -> str:
    """Return the final path component, tolerating ``/`` and ``\\`` separators."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _wav_basename_from_glc(glc_file: Path) -> str | None:
    """Return the ``.wav`` basename named inside a ``.glc``'s ``<data_source>``.

    The on-PC GLC viewer resolves the ``.wav`` adjacent to its ``.glc`` via
    this inner ``<filename>``; rehydration mirrors that lookup to restore the
    pair. Returns ``None`` if the ``.glc`` cannot be parsed.
    """
    try:
        root = ET.parse(glc_file).getroot()
    except (OSError, ET.ParseError) as exc:
        LOGGER.warning("Could not parse master .glc for wav adjacency: %s (%s)",
                       glc_file, exc)
        return None
    node = root.find(".//data_source/filename")
    if node is None:
        node = root.find(".//filename")
    if node is None or not (node.text or "").strip():
        return None
    return _basename(node.text.strip())


def _copy_back(master_file: Path, dest: Path, *, dry_run: bool) -> None:
    """Copy ``master_file`` to ``dest`` (mtime-preserving), tolerating absence."""
    if dry_run:
        LOGGER.info("[dry-run] would restore %s -> %s", master_file, dest.name)
        return
    if not master_file.is_file():
        # Mirror the generator's dangling-asset tolerance: the href is still
        # re-localised, so dropping the file in and re-running resolves it.
        LOGGER.warning("Master file missing, local copy will dangle: %s", master_file)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(master_file, dest)


def _rehydrate_section(
    section: ET.Element, topic_dir: Path, data: ET.Element, *, dry_run: bool,
) -> str | None:
    """Restore one redirected lofar ``<section>``; return its gram-relative note.

    Returns a short human-readable description of what was restored (for
    logging), or ``None`` if the section did not carry a recognisable link.
    """
    original_path = data.get("value", "")
    local_slug = slugify_asset_name(_basename(original_path))

    image = section.find(".//image")
    xref = section.find(".//xref")

    if image is not None and image.get("href"):
        master_file = (topic_dir / image.get("href")).resolve(strict=False)
        _copy_back(master_file, topic_dir / local_slug, dry_run=dry_run)
        if not dry_run:
            image.set("href", local_slug)
        link = image
        restored = local_slug
    elif xref is not None and xref.get("href"):
        master_glc = (topic_dir / xref.get("href")).resolve(strict=False)
        _copy_back(master_glc, topic_dir / local_slug, dry_run=dry_run)
        # Restore the adjacent .wav (the pair) named inside the master .glc.
        wav_base = _wav_basename_from_glc(master_glc)
        if wav_base:
            wav_slug = slugify_asset_name(wav_base)
            master_wav = master_glc.parent / wav_slug
            _copy_back(master_wav, topic_dir / wav_slug, dry_run=dry_run)
            restored = f"{local_slug} + {wav_slug}"
        else:
            restored = local_slug
        if not dry_run:
            xref.set("href", local_slug)
        link = xref
    else:
        LOGGER.warning(
            "Redirected section in %s has no <image>/<xref> link; skipping.",
            topic_dir,
        )
        return None

    if not dry_run:
        section.remove(data)
    return restored


def rehydrate_topic(topic_path: Path, *, dry_run: bool) -> int:
    """Rehydrate every redirected lofar in one topic; return lofars restored."""
    topic_dir = topic_path.parent
    tree = ET.parse(topic_path)
    root = tree.getroot()
    count = 0
    for section in root.iter("section"):
        data = section.find(f"data[@name='{ORIGINAL_ASSET_PATH}']")
        if data is None:
            continue  # not a redirected lofar — leave untouched (no-op)
        restored = _rehydrate_section(section, topic_dir, data, dry_run=dry_run)
        if restored is None:
            continue
        count += 1
        LOGGER.info(
            "Rehydrated lofar in %s: restored %s (master via %s)",
            topic_path.name, restored, data.get("value", ""),
        )
    if count and not dry_run:
        _write_text(topic_path, _serialise(root))
    return count


def _selected(topic_path: Path, gram: str | None) -> bool:
    """True if ``topic_path`` is within the requested ``--gram`` folder (or all)."""
    if gram is None:
        return True
    return gram in topic_path.parts


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reverse large-asset deduplication: restore redirected "
                    "lofars to self-contained grams (feature 006).",
    )
    parser.add_argument("--dita", required=True, type=Path,
                        help="root of the generated DITA tree to rehydrate")
    parser.add_argument("--gram", default=None,
                        help="restrict to a single gram folder, e.g. gram-12")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="report what would change without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)

    setup_logging(Path("rehydrate.log"))

    if not args.dita.is_dir():
        LOGGER.error("DITA tree does not exist: %s", args.dita)
        return 1

    total = 0
    for topic_path in sorted(args.dita.rglob("*.dita")):
        if not _selected(topic_path, args.gram):
            continue
        try:
            total += rehydrate_topic(topic_path, dry_run=args.dry_run)
        except ET.ParseError as exc:
            LOGGER.error("Failed to parse %s: %s", topic_path, exc)

    LOGGER.info(
        "Rehydration summary: lofars_restored=%d%s",
        total, " (dry-run, nothing written)" if args.dry_run else "",
    )
    return 0


if __name__ == "__main__":
    rc = main()
    if rc and not hasattr(sys, "ps1"):
        sys.exit(rc)
