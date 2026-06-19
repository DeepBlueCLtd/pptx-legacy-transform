#!/usr/bin/env python3
"""Build the deterministic air-gap deliverable zip for a GitHub release.

The archive mirrors "Project layout on the target" (README.md), the
layout the repo itself now follows: the canonical scripts ship from
``scripts/`` as-is; ``static/``, ``theme/`` (Oxygen overlays such as the
GramFrame plugin), ``stock.wav``, ``requirements.txt`` and ``README.md``
sit at the archive root. The operator extracts it straight
over ``ROOT\\`` on the target — the dev-only mock tooling, ``source\\``
and ``reports\\`` are not in the archive.

The root-level wrapper templates (``extract.py`` … ``snapshot.py`` plus
the ``pipeline.py`` orchestrator) ship under a ``wrappers/`` subfolder,
**not** at the archive root: an extract-over-``ROOT\\`` upgrade lands them
in ``ROOT\\wrappers\\`` and so never clobbers the operator's tuned
root-level copies. The operator copies up any new or missing wrapper (a
fresh ``pipeline.py``, say) by hand and tunes its Config block once — see
README.md, "Getting pipeline updates onto the target".

Determinism: entries are sorted, every zip timestamp comes from
``--timestamp`` (CI passes the commit date), and the permission/platform
fields are pinned — re-packaging the same commit yields a byte-identical
archive, matching the pipeline's idempotency invariant.

Dev-host / CI tool only: this script is not part of the delivered
pipeline and never runs on the air-gapped target.
"""
from __future__ import annotations

import argparse
import sys
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Loose files copied to the archive root (target ROOT\). run_pipeline.bat is
# deliberately absent: it is a dev-host orchestrator, never used on target.
ROOT_FILES = ("README.md", "requirements.txt", "stock.wav")

# Root-level wrapper templates (and the pipeline.py orchestrator). They ship
# under wrappers/ in the archive, never at the root, so an extract-over-ROOT\
# upgrade can't overwrite the operator's tuned root-level copies; the operator
# copies up any new/missing wrapper by hand. These are the only repo-root *.py
# files, so the set is discovered rather than hand-listed.
WRAPPERS = tuple(sorted(p.name for p in REPO_ROOT.glob("*.py")))

# Dev-host-only helpers living in scripts/ that must not ship; every other
# scripts/*.py is a canonical pipeline stage.
DEV_ONLY_SCRIPTS = frozenset({"generate_mock_analysis_sheet.py"})

# 1980-01-01, the zip format's epoch: the stamp used when no commit date is
# supplied, and the earliest one the format can store.
ZIP_EPOCH = 315532800


def collect_entries():
    """Return (source path, archive name) pairs sorted by archive name."""
    entries = []
    for path in (REPO_ROOT / "scripts").glob("*.py"):
        if path.name in DEV_ONLY_SCRIPTS:
            continue
        entries.append((path, "scripts/" + path.name))
    for name in ROOT_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            entries.append((path, name))
        else:
            print(f"WARNING: expected root file missing: {name}", file=sys.stderr)
    for name in WRAPPERS:
        path = REPO_ROOT / name
        if path.is_file():
            entries.append((path, "wrappers/" + name))
    static_root = REPO_ROOT / "static"
    if static_root.is_dir():
        for path in static_root.rglob("*"):
            if path.is_file():
                entries.append((path, path.relative_to(REPO_ROOT).as_posix()))
    else:
        print("WARNING: static/ missing; archive carries no common pages", file=sys.stderr)
    # theme/ carries the Oxygen overlay(s) the operator installs into the
    # production publisher (e.g. the GramFrame plugin bundle + head fragment).
    # Unlike scripts/vendor/ (dev/CI-only), these must reach the air-gapped box.
    theme_root = REPO_ROOT / "theme"
    if theme_root.is_dir():
        for path in theme_root.rglob("*"):
            if path.is_file():
                entries.append((path, path.relative_to(REPO_ROOT).as_posix()))
    else:
        print("WARNING: theme/ missing; archive carries no Oxygen overlays", file=sys.stderr)
    return sorted(entries, key=lambda entry: entry[1])


def build_zip(out_path, timestamp=ZIP_EPOCH):
    """Write the archive and return the (path, arcname) entries packed."""
    date_time = time.gmtime(timestamp)[:6]
    entries = collect_entries()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w") as archive:
        for path, arcname in entries:
            info = zipfile.ZipInfo(arcname, date_time=date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3            # pin "unix" whatever the build host
            info.external_attr = 0o644 << 16  # rw-r--r-- regular file
            archive.writestr(info, path.read_bytes())
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="path of the zip to write")
    parser.add_argument(
        "--timestamp",
        type=int,
        default=ZIP_EPOCH,
        help="unix time stamped on every archive entry (CI passes the commit date)",
    )
    args = parser.parse_args(argv)
    entries = build_zip(Path(args.out), args.timestamp)
    for _, arcname in entries:
        print(arcname)
    print(f"wrote {args.out} ({len(entries)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
