"""Publish the generated DITA tree to HTML using DITA-OT.

The DITA source files in ``dita/`` deliberately omit DOCTYPE declarations
(contract: Oxygen handles DTD validation at publish time). DITA-OT,
however, needs DOCTYPEs to classify the elements. This script stages a
build copy of ``dita/`` with DOCTYPEs injected, runs DITA-OT once per
ditamap, and writes the results under ``html/``.

The source ``dita/`` tree is never modified.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

_OUTER_IMAGE = re.compile(r'<image\s[^>]*href="(?:\.\./)+[^"]*"[^/]*/>')

TOPIC_DOCTYPE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA Topic//EN" "topic.dtd">\n'
)
MAP_DOCTYPE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">\n'
)


def stage(src: Path, dst: Path) -> None:
    """Copy src to dst, add DOCTYPEs, and promote ditamaps to the staged root.

    Source ditamaps live under ``ditamaps/`` with ``../`` hrefs into the
    chapter tree. DITA-OT preserves those relative paths in its output,
    which buries the HTML under a parent-walk path. Promoting the ditamap
    one level up (and stripping ``../`` from each href) keeps the HTML
    output tree flat.
    """
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for path in dst.rglob("*.dita"):
        body = path.read_text(encoding="utf-8")
        body = _OUTER_IMAGE.sub("<!-- image stripped for HTML preview -->", body)
        path.write_text(TOPIC_DOCTYPE + body, encoding="utf-8", newline="\n")
    ditamap_dir = dst / "ditamaps"
    for path in sorted(ditamap_dir.glob("*.ditamap")):
        body = path.read_text(encoding="utf-8").replace('href="../', 'href="')
        (dst / path.name).write_text(MAP_DOCTYPE + body, encoding="utf-8", newline="\n")
    shutil.rmtree(ditamap_dir)


def publish(dita_ot: Path, staged: Path, out_root: Path) -> int:
    ditamaps = sorted(staged.glob("*.ditamap"))
    if not ditamaps:
        print(f"No ditamaps found under {staged}/ditamaps", file=sys.stderr)
        return 1
    errors = 0
    for ditamap in ditamaps:
        target = out_root / ditamap.stem
        print(f"[publish] {ditamap.name} -> {target}")
        target.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                str(dita_ot / "bin" / "dita"),
                f"--input={ditamap}",
                "--format=html5",
                f"--output={target}",
                "--processing-mode=lax",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors += 1
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
    return 0 if errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dita", default=Path("dita"), type=Path)
    parser.add_argument("--out", default=Path("html"), type=Path)
    parser.add_argument("--dita-ot", required=True, type=Path)
    parser.add_argument("--staged", default=Path(".dita-build"), type=Path)
    args = parser.parse_args(argv)

    if not args.dita.is_dir():
        print(f"Source dita tree not found: {args.dita}", file=sys.stderr)
        return 1
    if not (args.dita_ot / "bin" / "dita").exists():
        print(f"DITA-OT not found at {args.dita_ot}", file=sys.stderr)
        return 1

    print(f"[stage] {args.dita} -> {args.staged}")
    stage(args.dita, args.staged)

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    rc = publish(args.dita_ot, args.staged, args.out)

    shutil.rmtree(args.staged, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
