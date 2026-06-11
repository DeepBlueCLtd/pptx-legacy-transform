"""A LibreOffice-free renderer stub for the snapshotter tests (research R6).

Mimics ``soffice --headless --convert-to {png|pdf} --outdir <dir> <doc>``:

- ``--convert-to png`` writes a tiny valid PNG (the project's existing byte
  template, reused from ``mock_pptx.emit_png``) named ``<doc-stem>.png`` into
  ``--outdir``.
- ``--convert-to pdf`` writes a minimal single-page PDF whose page tree carries
  ``/Count N`` so the snapshotter's stdlib page-count read works.

Behaviour is configurable via environment variables so one stub serves the
success, failure, and multi-page test cases without LibreOffice:

- ``FAKE_RENDERER_EXIT`` (default ``0``): exit with this code (non-zero
  simulates a render failure).
- ``FAKE_RENDERER_PAGES`` (default ``1``): the ``/Count`` written into the PDF.

Kept stdlib-only so the canonical suite stays LibreOffice-free.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mock_pptx import emit_png  # noqa: E402


def _write_min_pdf(path: Path, pages: int) -> None:
    """Write a minimal PDF whose page tree declares ``/Count <pages>``.

    Not a fully spec-conformant PDF -- just enough cleartext structure for the
    snapshotter's tolerant ``/Type /Pages /Count N`` scan to read the count.
    """
    body = (
        "%PDF-1.4\n"
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count "
        f"{pages} >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
        "trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )
    path.write_bytes(body.encode("ascii"))


def main(argv: list[str] | None = None) -> int:
    exit_code = int(os.environ.get("FAKE_RENDERER_EXIT", "0"))
    if exit_code != 0:
        sys.stderr.write("fake_renderer: simulated render failure\n")
        return exit_code

    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--convert-to", dest="convert_to", required=True)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("doc", type=Path)
    args = parser.parse_args(argv)

    args.outdir.mkdir(parents=True, exist_ok=True)
    stem = args.doc.stem
    if args.convert_to == "png":
        emit_png(args.outdir / f"{stem}.png")
    elif args.convert_to == "pdf":
        pages = int(os.environ.get("FAKE_RENDERER_PAGES", "1"))
        _write_min_pdf(args.outdir / f"{stem}.pdf", pages)
    else:
        sys.stderr.write(f"fake_renderer: unsupported --convert-to {args.convert_to}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
