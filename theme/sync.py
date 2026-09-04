#!/usr/bin/env python3
"""Theme development loop: overlays -> template -> published build.

Dev-host-only (the packager skips ``theme/*.py``), and stdlib-only like the
rest of the suite.

The design surface is the *real* Oxygen output, not the DITA-OT dev preview:
Oxygen's WebHelp Responsive chrome (``#wh_topic_toc``, ``.wh_content_area``,
the tiles welcome page) exists in no other renderer, so a rule tuned anywhere
else has to be re-verified here anyway.

Run it with no arguments after *anything* — a stylesheet edit or a republish.
It does three things, each idempotent:

1. Copies every overlay payload under ``theme/<overlay>/`` into the wired
   template ``theme/pptx-transform/`` — the copies
   ``tests/test_package_release.py`` byte-compares.
2. Copies those on into the ``oxygen-webhelp/template/`` folder of each
   published build — one per publication, at ``published/<edition>/<pub>/`` —
   so a CSS or JS edit is live in the browser on a hard refresh with **no
   republish**: Oxygen deploys these files verbatim.
3. Normalises the per-publish stamps a fresh Oxygen publish leaves in
   ``demo/oxygen-sample/published/`` (see ``_normalise``).  That tree is
   committed, and without this every republish would rewrite every page and
   bury the design change in the diff.

Republish from Oxygen (the scenarios write straight into ``published/``) only
when the DITA or a ``.opt`` parameter changed; for CSS/JS, this is enough.
"""
from __future__ import annotations

import argparse
import filecmp
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THEME_ROOT = REPO_ROOT / "theme"
TEMPLATE = THEME_ROOT / "pptx-transform"
PUBLISHED = REPO_ROOT / "demo" / "oxygen-sample" / "published"

# Where Oxygen lands a publishing template's own files inside its output.
DEPLOYED_TEMPLATE = "oxygen-webhelp/template"

# Files that describe an overlay rather than being part of its payload.
NOT_PAYLOAD = {"README.md"}

# Not overlays, though they sit alongside them. __pycache__ is the one that
# bites: importing this module (rather than running it) leaves a directory
# here that otherwise reads as an overlay whose "payload" is a .pyc, and the
# template dutifully receives a copy.
NOT_OVERLAY = {"__pycache__"}

# Oxygen stamps each publish with a 14-digit timestamp (cache-buster on every
# asset href) and a generation date in the sitemap. Neither says anything about
# the design, and both would churn all ~30 pages on every republish, so the
# committed copy carries fixed values instead. The 10-digit ``buildId`` of the
# Oxygen *installation* is left alone — a change there is real news.
_SUBSTITUTIONS = (
    (re.compile(r"buildId=\d{14}\b"), "buildId=00000000000000"),
    (re.compile(r"<lastmod>[^<]*</lastmod>"), "<lastmod>2000-01-01T00:00:00Z</lastmod>"),
)
_TEXT_SUFFIXES = {".html", ".xml", ".js", ".css", ".txt", ".properties", ".json"}


def overlay_payloads():
    """Yield (source, path relative to an overlay root) for every payload file."""
    for overlay in sorted(THEME_ROOT.glob("*")):
        if not overlay.is_dir() or overlay == TEMPLATE:
            continue
        if overlay.name in NOT_OVERLAY:
            continue
        for src in sorted(overlay.rglob("*")):
            if src.is_file() and src.name not in NOT_PAYLOAD:
                yield src, src.relative_to(overlay)


def _copy(src: Path, dest: Path) -> bool:
    """Copy when the bytes differ; report whether anything was written."""
    if dest.is_file() and filecmp.cmp(src, dest, shallow=False):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def sync_template() -> int:
    """Overlay payloads -> the wired template. Returns the number written."""
    written = 0
    for src, rel in overlay_payloads():
        if _copy(src, TEMPLATE / rel):
            print(f"  template  {rel.as_posix()}")
            written += 1
    return written


def published_builds():
    """Every published build — any folder holding a deployed template copy.

    Oxygen writes one build per publication, and each scenario's output folder
    ends in ``${cfn}`` (the ditamap's own name), so the builds sit at
    ``published/<edition>/<publication>/``.  Older trees put a single build
    straight at ``published/<edition>/``.

    Search at any depth rather than assuming either shape: a build root is
    simply a folder with an ``oxygen-webhelp/template`` inside it.  Looking
    only one level down used to mean that clearing an edition's root build
    left this matching nothing at all — and then sync.py reported "everything
    already in sync" while deploying nothing and normalising nothing.
    """
    if not PUBLISHED.is_dir():
        return []
    return sorted({
        deployed.parent.parent
        for deployed in PUBLISHED.glob("**/" + DEPLOYED_TEMPLATE)
        if deployed.is_dir()
    })


def sync_builds() -> int:
    """Template files -> each published build, for refresh-to-see editing.

    Only files the publish already deployed are refreshed.  Oxygen decides
    what lands there (the ``.opt`` itself, the preview images and the head
    fragments never do), and inventing files the real publish would not
    write turns the committed build into a fiction.
    """
    written = 0
    for build in published_builds():
        deployed = build / DEPLOYED_TEMPLATE
        label = build.relative_to(PUBLISHED).as_posix()
        for src in sorted(TEMPLATE.rglob("*")):
            if not src.is_file():
                continue
            dest = deployed / src.relative_to(TEMPLATE)
            if not dest.is_file():
                continue
            if _copy(src, dest):
                print(f"  {label}  {src.relative_to(TEMPLATE).as_posix()}")
                written += 1
    return written


def _normalise(path: Path) -> bool:
    """Rewrite the per-publish stamps in one published file, in place.

    Returns whether the file was changed.
    """
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    swapped = text
    for pattern, replacement in _SUBSTITUTIONS:
        swapped = pattern.sub(replacement, swapped)
    if swapped != text:
        # Path.write_text has no newline kwarg on the 3.9 floor, and the
        # captured bytes must survive the round trip unchanged.
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(swapped)
        return True
    return False


def normalise_builds() -> int:
    """Strip the per-publish stamps from every committed build. Idempotent.

    Collect the files first: an older root-level build and the per-publication
    builds beneath it are both build roots, so walking each in turn would visit
    the nested ones twice and double-count them.
    """
    files = {
        path
        for build in published_builds()
        for path in build.rglob("*")
        if path.is_file()
    }
    return sum(1 for path in sorted(files) if _normalise(path))


def main(argv=None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)

    into_template = sync_template()
    into_builds = sync_builds()
    normalised = normalise_builds()

    if not (into_template or into_builds or normalised):
        print("everything already in sync")
        return 0
    print(f"{into_template} file(s) -> template, {into_builds} -> published build(s)")
    if into_builds:
        print("hard-refresh the browser to see it (no republish needed)")
    if normalised:
        print(f"{normalised} published file(s) had their publish stamps normalised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
